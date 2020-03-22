from __future__ import annotations

import asyncio
import contextvars
import datetime
import json
import uuid
import random
import logging
import threading
from asyncio.base_futures import CancelledError
from asyncio.events import AbstractEventLoop
from asyncio.futures import Future
from asyncio.tasks import Task
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any, Callable

from more_itertools import peekable

from cadence.activity_method import ExecuteActivityParameters
from cadence.cadence_types import PollForDecisionTaskRequest, TaskList, PollForDecisionTaskResponse, \
    RespondDecisionTaskCompletedRequest, \
    CompleteWorkflowExecutionDecisionAttributes, Decision, DecisionType, RespondDecisionTaskCompletedResponse, \
    HistoryEvent, EventType, WorkflowType, ScheduleActivityTaskDecisionAttributes, \
    CancelWorkflowExecutionDecisionAttributes, StartTimerDecisionAttributes, TimerFiredEventAttributes, \
    FailWorkflowExecutionDecisionAttributes, RecordMarkerDecisionAttributes, Header, WorkflowQuery, \
    RespondQueryTaskCompletedRequest, QueryTaskCompletedType, QueryWorkflowResponse
from cadence.conversions import json_to_args, args_to_json
from cadence.decisions import DecisionId, DecisionTarget
from cadence.exception_handling import serialize_exception, deserialize_exception
from cadence.exceptions import WorkflowTypeNotFound, NonDeterministicWorkflowException, ActivityTaskFailedException, \
    ActivityTaskTimeoutException, SignalNotFound, ActivityFailureException, QueryNotFound, QueryDidNotComplete
from cadence.state_machines import ActivityDecisionStateMachine, DecisionStateMachine, CompleteWorkflowStateMachine, \
    TimerDecisionStateMachine, MarkerDecisionStateMachine
from cadence.tchannel import TChannelException
from cadence.worker import Worker
from cadence.workflow import QueryMethod
from cadence.workflowservice import WorkflowService

logger = logging.getLogger(__name__)


def is_decision_event(event: HistoryEvent) -> bool:
    decision_event_types = (EventType.ActivityTaskScheduled,
                            EventType.StartChildWorkflowExecutionInitiated,
                            EventType.TimerStarted,
                            EventType.WorkflowExecutionCompleted,
                            EventType.WorkflowExecutionFailed,
                            EventType.WorkflowExecutionCanceled,
                            EventType.WorkflowExecutionContinuedAsNew,
                            EventType.ActivityTaskCancelRequested,
                            EventType.RequestCancelActivityTaskFailed,
                            EventType.TimerCanceled,
                            EventType.CancelTimerFailed,
                            EventType.RequestCancelExternalWorkflowExecutionInitiated,
                            EventType.MarkerRecorded,
                            EventType.SignalExternalWorkflowExecutionInitiated)
    return event.event_type in decision_event_types


def nano_to_milli(nano):
    return nano/(1000 * 1000)


class HistoryHelper:

    def __init__(self, events: List[HistoryEvent]):
        self.events = peekable(events)

    def has_next(self) -> bool:
        try:
            self.events.peek()
            return True
        except StopIteration:
            return False

    def next(self) -> Optional[DecisionEvents]:
        events = self.events
        if not self.has_next():
            return None
        decision_events: List[HistoryEvent] = []
        new_events: List[HistoryEvent] = []
        replay = True
        next_decision_event_id = -1
        # noinspection PyUnusedLocal
        event: HistoryEvent
        for event in events:
            event_type = event.event_type
            if event_type == EventType.DecisionTaskStarted or not self.has_next():
                replay_current_time_milliseconds = nano_to_milli(event.timestamp)
                if not self.has_next():
                    replay = False
                    next_decision_event_id = event.event_id + 2
                    break
                peeked: HistoryEvent = events.peek()
                peeked_type = peeked.event_type
                if peeked_type == EventType.DecisionTaskTimedOut or peeked_type == EventType.DecisionTaskFailed:
                    continue
                elif peeked_type == EventType.DecisionTaskCompleted:
                    next(events)
                    next_decision_event_id = peeked.event_id + 1
                    break
                else:
                    raise Exception(
                        "Unexpected event after DecisionTaskStarted: {}".format(peeked))
            new_events.append(event)
        while self.has_next():
            if not is_decision_event(events.peek()):
                break
            decision_events.append(next(events))
        result = DecisionEvents(new_events, decision_events, replay,
                                replay_current_time_milliseconds, next_decision_event_id)
        logger.debug("HistoryHelper next=%s", result)
        return result


@dataclass
class DecisionEvents:
    events: List[HistoryEvent]
    decision_events: List[HistoryEvent]
    replay: bool
    replay_current_time_milliseconds: int
    next_decision_event_id: int
    markers: List[HistoryEvent] = field(default_factory=list)

    def __post_init__(self):
        for event in self.decision_events:
            if event.event_type == EventType.MarkerRecorded:
                self.markers.append(event)

    def get_optional_decision_event(self, event_id) -> HistoryEvent:
        index = event_id - self.next_decision_event_id
        if index < 0 or index >= len(self.decision_events):
            return None
        else:
            return self.decision_events[index]


class Status(Enum):
    CREATED = 1
    RUNNING = 2
    DONE = 3


current_task = contextvars.ContextVar("current_task")


@dataclass
class ITask:
    decider: ReplayDecider = None
    task: Task = None
    status: Status = Status.CREATED
    awaited: Future = None

    def is_done(self):
        return self.status == Status.DONE

    def destroy(self):
        if self.status == Status.RUNNING:
            self.status = Status.DONE
            self.task.cancel()

    def start(self):
        pass

    async def await_till(self, c: Callable, timeout_seconds: int = 0) -> bool:
        timer_cancellation_handler: TimerCancellationHandler = None
        timer_fired = False

        def timer_callback(ex: Exception):
            nonlocal timer_fired
            if not ex:
                timer_fired = True

        if timeout_seconds:
            timer_cancellation_handler = self.decider.decision_context.create_timer(delay_seconds=timeout_seconds, callback=timer_callback)

        while not c() and not timer_fired:
            self.awaited = self.decider.event_loop.create_future()
            await self.awaited
            assert self.awaited.done()

        self.awaited = None

        if timer_fired:
            return False

        if timer_cancellation_handler:
            timer_cancellation_handler.accept(None)

        return True

    def unblock(self):
        if self.awaited:
            self.awaited.set_result(None)

    @staticmethod
    def current() -> ITask:
        return current_task.get()


@dataclass
class WorkflowMethodTask(ITask):
    task_id: str = None
    workflow_input: List = None
    worker: Worker = None
    workflow_type: WorkflowType = None
    workflow_instance: object = None
    ret_value: object = None

    def __post_init__(self):
        logger.debug(f"[task-{self.task_id}] Created")
        self.task = asyncio.get_event_loop().create_task(self.init_workflow_instance())

    async def init_workflow_instance(self):
        current_task.set(self)
        cls, _ = self.worker.get_workflow_method(self.workflow_type.name)
        try:
            self.workflow_instance = cls()
            self.task = asyncio.get_event_loop().create_task(self.workflow_main())
        except Exception as ex:
            logger.error(
                f"Initialization of Workflow {self.workflow_type.name}({str(self.workflow_input)[1:-1]}) failed", exc_info=1)
            self.decider.fail_workflow_execution(ex)
            self.status = Status.DONE

    async def workflow_main(self):
        logger.debug(f"[task-{self.task_id}] Running")

        if self.is_done():
            return

        current_task.set(self)

        if self.workflow_type.name not in self.worker.workflow_methods:
            self.status = Status.DONE
            ex = WorkflowTypeNotFound(self.workflow_type.name)
            logger.error(f"Workflow type not found: {self.workflow_type.name}")
            self.decider.fail_workflow_execution(ex)
            return

        cls, workflow_proc = self.worker.workflow_methods[self.workflow_type.name]
        self.status = Status.RUNNING
        try:
            logger.info(f"Invoking workflow {self.workflow_type.name}({str(self.workflow_input)[1:-1]})")
            self.ret_value = await workflow_proc(self.workflow_instance, *self.workflow_input)
            logger.info(
                f"Workflow {self.workflow_type.name}({str(self.workflow_input)[1:-1]}) returned {self.ret_value}")
            self.decider.complete_workflow_execution(self.ret_value)
        except CancelledError:
            logger.debug("Coroutine cancelled (expected)")
        except Exception as ex:
            logger.error(
                f"Workflow {self.workflow_type.name}({str(self.workflow_input)[1:-1]}) failed", exc_info=1)
            self.decider.fail_workflow_execution(ex)
        finally:
            self.status = Status.DONE

    def get_workflow_instance(self):
        return self.workflow_instance


@dataclass
class QueryMethodTask(ITask):
    task_id: str = None
    workflow_instance: object = None
    query_name: str = None
    query_input: List = None
    exception_thrown: BaseException = None
    ret_value: object = None

    def start(self):
        logger.debug(f"[query-task-{self.task_id}-{self.query_name}] Created")
        self.task = asyncio.get_event_loop().create_task(self.query_main())

    async def query_main(self):
        logger.debug(f"[query-task-{self.task_id}-{self.query_name}] Running")
        current_task.set(self)

        if not self.query_name in self.workflow_instance._query_methods:
            self.status = Status.DONE
            self.exception_thrown = QueryNotFound(self.query_name)
            logger.error(f"Query not found: {self.query_name}")
            return

        query_proc = self.workflow_instance._query_methods[self.query_name]
        self.status = Status.RUNNING

        try:
            logger.info(f"Invoking query {self.query_name}({str(self.query_input)[1:-1]})")
            self.ret_value = await query_proc(self.workflow_instance, *self.query_input)
            logger.info(
                f"Query {self.query_name}({str(self.query_input)[1:-1]}) returned {self.ret_value}")
        except CancelledError:
            logger.debug("Coroutine cancelled (expected)")
        except Exception as ex:
            logger.error(
                f"Query {self.query_name}({str(self.query_input)[1:-1]}) failed", exc_info=1)
            self.exception_thrown = ex
        finally:
            self.status = Status.DONE


@dataclass
class SignalMethodTask(ITask):
    task_id: str = None
    workflow_instance: object = None
    signal_name: str = None
    signal_input: List = None
    exception_thrown: BaseException = None
    ret_value: object = None

    def start(self):
        logger.debug(f"[signal-task-{self.task_id}-{self.signal_name}] Created")
        self.task = asyncio.get_event_loop().create_task(self.signal_main())

    async def signal_main(self):
        logger.debug(f"[signal-task-{self.task_id}-{self.signal_name}] Running")
        current_task.set(self)

        if not self.signal_name in self.workflow_instance._signal_methods:
            self.status = Status.DONE
            self.exception_thrown = SignalNotFound(self.signal_name)
            logger.error(f"Signal not found: {self.signal_name}")
            return

        signal_proc = self.workflow_instance._signal_methods[self.signal_name]
        self.status = Status.RUNNING

        try:
            logger.info(f"Invoking signal {self.signal_name}({str(self.signal_input)[1:-1]})")
            self.ret_value = await signal_proc(self.workflow_instance, *self.signal_input)
            logger.info(
                f"Signal {self.signal_name}({str(self.signal_input)[1:-1]}) returned {self.ret_value}")
            self.decider.complete_signal_execution(self)
        except CancelledError:
            logger.debug("Coroutine cancelled (expected)")
        except Exception as ex:
            logger.error(
                f"Signal {self.signal_name}({str(self.signal_input)[1:-1]}) failed", exc_info=1)
            self.exception_thrown = ex
        finally:
            self.status = Status.DONE


@dataclass
class EventLoopWrapper:
    event_loop: AbstractEventLoop = None

    def __post_init__(self):
        self.event_loop = asyncio.get_event_loop()

    def run_event_loop_once(self):
        self.event_loop.call_soon(self.event_loop.stop)
        self.event_loop.run_forever()

    def create_future(self) -> Future[Any]:
        return self.event_loop.create_future()


@dataclass
class DecisionContext:
    decider: ReplayDecider
    scheduled_activities: Dict[int, Future[bytes]] = field(default_factory=dict)
    workflow_clock: ClockDecisionContext = None
    current_run_id: str = None

    def __post_init__(self):
        if not self.workflow_clock:
            self.workflow_clock = ClockDecisionContext(self.decider, self)

    async def schedule_activity_task(self, parameters: ExecuteActivityParameters):
        attr = ScheduleActivityTaskDecisionAttributes()
        attr.activity_type = parameters.activity_type
        attr.input = parameters.input
        if parameters.heartbeat_timeout_seconds > 0:
            attr.heartbeat_timeout_seconds = parameters.heartbeat_timeout_seconds
        attr.schedule_to_close_timeout_seconds = parameters.schedule_to_close_timeout_seconds
        attr.schedule_to_start_timeout_seconds = parameters.schedule_to_start_timeout_seconds
        attr.start_to_close_timeout_seconds = parameters.start_to_close_timeout_seconds
        attr.activity_id = parameters.activity_id
        if not attr.activity_id:
            attr.activity_id = self.decider.get_and_increment_next_id()
        attr.task_list = TaskList()
        attr.task_list.name = parameters.task_list

        if parameters.retry_parameters:
            attr.retry_policy = parameters.retry_parameters.to_retry_policy()

        scheduled_event_id = self.decider.schedule_activity_task(schedule=attr)
        future = self.decider.event_loop.create_future()
        self.scheduled_activities[scheduled_event_id] = future
        try:
            await future
        except CancelledError as e:
            logger.debug("Coroutine cancelled (expected)")
            raise e
        except Exception as ex:
            pass
        ex = future.exception()
        if ex:
            activity_failure = ActivityFailureException(scheduled_event_id,
                                                        parameters.activity_type.name,
                                                        parameters.activity_id,
                                                        serialize_exception(ex))
            raise activity_failure
        assert future.done()
        raw_bytes = future.result()
        return json.loads(str(raw_bytes, "utf-8"))

    async def schedule_timer(self, seconds: int):
        future = self.decider.event_loop.create_future()

        def callback(ex: Exception):
            nonlocal future
            if ex:
                future.set_exception(ex)
            else:
                future.set_result("time-fired")

        self.decider.decision_context.create_timer(delay_seconds=seconds, callback=callback)
        await future
        assert future.done()
        exception = future.exception()
        if exception:
            raise exception
        return

    def handle_activity_task_completed(self, event: HistoryEvent):
        attr = event.activity_task_completed_event_attributes
        if self.decider.handle_activity_task_closed(attr.scheduled_event_id):
            future = self.scheduled_activities.get(attr.scheduled_event_id)
            if future:
                self.scheduled_activities.pop(attr.scheduled_event_id)
                future.set_result(attr.result)
            else:
                raise NonDeterministicWorkflowException(
                    f"Trying to complete activity event {attr.scheduled_event_id} that is not in scheduled_activities")

    def handle_activity_task_failed(self, event: HistoryEvent):
        attr = event.activity_task_failed_event_attributes
        if self.decider.handle_activity_task_closed(attr.scheduled_event_id):
            future = self.scheduled_activities.get(attr.scheduled_event_id)
            if future:
                self.scheduled_activities.pop(attr.scheduled_event_id)
                # TODO: attr.reason - what should we do with it?
                ex = deserialize_exception(attr.details)
                future.set_exception(ex)
            else:
                raise NonDeterministicWorkflowException(
                    f"Trying to complete activity event {attr.scheduled_event_id} that is not in scheduled_activities")

    def handle_activity_task_timed_out(self, event: HistoryEvent):
        attr = event.activity_task_timed_out_event_attributes
        if self.decider.handle_activity_task_closed(attr.scheduled_event_id):
            future = self.scheduled_activities.get(attr.scheduled_event_id)
            if future:
                self.scheduled_activities.pop(attr.scheduled_event_id)
                ex = ActivityTaskTimeoutException(event.event_id, attr.timeout_type, attr.details)
                future.set_exception(ex)
            else:
                raise NonDeterministicWorkflowException(
                    f"Trying to complete activity event {attr.scheduled_event_id} that is not in scheduled_activities")

    def create_timer(self, delay_seconds: int, callback: Callable):
        return self.workflow_clock.create_timer(delay_seconds, callback)

    def set_replay_current_time_milliseconds(self, replay_current_time_milliseconds: int):
        if replay_current_time_milliseconds < self.workflow_clock.current_time_millis():
            raise Exception("workflow clock moved back")
        self.workflow_clock.set_replay_current_time_milliseconds(replay_current_time_milliseconds)

    def current_time_millis(self):
        return self.workflow_clock.current_time_millis()

    def set_replaying(self, replaying: bool):
        self.workflow_clock.set_replaying(replaying)

    def is_replaying(self):
        return self.workflow_clock.is_replaying()

    def handle_timer_fired(self, attributes: TimerFiredEventAttributes):
        self.workflow_clock.handle_timer_fired(attributes)

    def handle_timer_canceled(self, event: HistoryEvent):
        self.workflow_clock.handle_timer_canceled(event)

    def set_current_run_id(self, run_id: str):
        self.current_run_id = run_id

    def random_uuid(self) -> uuid.UUID:
        return uuid.uuid3(uuid.UUID(self.current_run_id), str(self.decider.get_and_increment_next_id()))

    def new_random(self) -> random.Random:
        random_uuid = self.random_uuid()
        lsb = random_uuid.bytes[:8]
        generator = random.Random()
        generator.seed(lsb, version=2)
        return generator

    def record_marker(self, marker_name: str, header: Header, details: bytes):
        marker = RecordMarkerDecisionAttributes()
        marker.marker_name = marker_name
        marker.header = header
        marker.details = details
        decision = Decision()
        decision.decision_type = DecisionType.RecordMarker
        decision.record_marker_decision_attributes = marker
        next_decision_event_id = self.decider.next_decision_event_id
        decision_id = DecisionId(DecisionTarget.MARKER, next_decision_event_id)
        self.decider.add_decision(decision_id, MarkerDecisionStateMachine(id=decision_id, decision=decision))

    def get_version(self, change_id: str, min_supported: int, max_supported: int) -> int:
        return self.workflow_clock.get_version(change_id, min_supported, max_supported)

    def get_logger(self, name) -> logging.Logger:
        replay_aware_logger = logging.getLogger(name)
        make_replay_aware(replay_aware_logger)
        return replay_aware_logger


@dataclass
class ReplayDecider:
    execution_id: str
    workflow_type: WorkflowType
    worker: Worker
    workflow_task: WorkflowMethodTask = None
    tasks: List[ITask] = field(default_factory=list)
    event_loop: EventLoopWrapper = field(default_factory=EventLoopWrapper)
    completed: bool = False

    next_decision_event_id: int = 0
    id_counter: int = 0
    decision_events: DecisionEvents = None
    decisions: OrderedDict[DecisionId, DecisionStateMachine] = field(default_factory=OrderedDict)
    decision_context: DecisionContext = None

    activity_id_to_scheduled_event_id: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        self.decision_context = DecisionContext(decider=self)

    def decide(self, events: List[HistoryEvent]):
        helper = HistoryHelper(events)
        while helper.has_next():
            decision_events = helper.next()
            self.process_decision_events(decision_events)
        return self.get_decisions()

    def process_decision_events(self, decision_events: DecisionEvents):
        self.decision_context.set_replaying(decision_events.replay)
        self.decision_context.set_replay_current_time_milliseconds(decision_events.replay_current_time_milliseconds)

        self.handle_decision_task_started(decision_events)
        for event in decision_events.markers:
            if not event.marker_recorded_event_attributes.marker_name == LOCAL_ACTIVITY_MARKER_NAME:
                self.process_event(event);
        for event in decision_events.events:
            self.process_event(event)
        if self.completed:
            return
        self.unblock_all()
        self.event_loop.run_event_loop_once()
        if decision_events.replay:
            self.notify_decision_sent()
        for event in decision_events.decision_events:
            self.process_event(event)

    def unblock_all(self):
        for t in self.tasks:
            t.unblock()

    def process_event(self, event: HistoryEvent):
        event_handler = event_handlers.get(event.event_type)
        if not event_handler:
            raise Exception(f"No event handler for event type {event.event_type.name}")
        event_handler(self, event)

    def handle_workflow_execution_started(self, event: HistoryEvent):
        start_event_attributes = event.workflow_execution_started_event_attributes
        self.decision_context.set_current_run_id(start_event_attributes.original_execution_run_id)
        if start_event_attributes.input is None or start_event_attributes.input == b'':
            workflow_input = []
        else:
            workflow_input = json_to_args(start_event_attributes.input)
        self.workflow_task = WorkflowMethodTask(task_id=self.execution_id, workflow_input=workflow_input,
                                                worker=self.worker, workflow_type=self.workflow_type, decider=self)
        self.event_loop.run_event_loop_once()
        assert self.workflow_task.workflow_instance
        self.tasks.append(self.workflow_task)

    def handle_workflow_execution_cancel_requested(self, event: HistoryEvent):
        self.cancel_workflow_execution()

    def notify_decision_sent(self):
        for state_machine in self.decisions.values():
            if state_machine.get_decision():
                state_machine.handle_decision_task_started_event()

    def handle_decision_task_started(self, decision_events: DecisionEvents):
        self.decision_events = decision_events
        self.next_decision_event_id = decision_events.next_decision_event_id

    def complete_workflow_execution(self, ret_value):
        # PORT: addAllMissingVersionMarker(false, Optional.empty());
        decision = Decision()
        attr = CompleteWorkflowExecutionDecisionAttributes()
        attr.result = json.dumps(ret_value)
        decision.complete_workflow_execution_decision_attributes = attr
        decision.decision_type = DecisionType.CompleteWorkflowExecution
        decision_id = DecisionId(DecisionTarget.SELF, 0)
        self.add_decision(decision_id, CompleteWorkflowStateMachine(decision_id, decision))
        self.completed = True

    def fail_workflow_execution(self, exception):
        # PORT: addAllMissingVersionMarker(false, Optional.empty());
        decision = Decision()
        fail_attributes = FailWorkflowExecutionDecisionAttributes()
        fail_attributes.reason = "WorkflowFailureException"
        fail_attributes.details = serialize_exception(exception)
        decision.fail_workflow_execution_decision_attributes = fail_attributes
        decision.decision_type = DecisionType.FailWorkflowExecution
        decision_id = DecisionId(DecisionTarget.SELF, 0)
        self.add_decision(decision_id, CompleteWorkflowStateMachine(decision_id, decision))
        self.completed = True

    def cancel_workflow_execution(self):
        logger.info("Canceling workflow: %s", self.execution_id)
        decision = Decision()
        attr = CancelWorkflowExecutionDecisionAttributes()
        attr.details = None
        decision.cancel_workflow_execution_decision_attributes = attr
        decision.decision_type = DecisionType.CancelWorkflowExecution
        decision_id = DecisionId(DecisionTarget.SELF, 0)
        self.add_decision(decision_id, CompleteWorkflowStateMachine(decision_id, decision))
        self.completed = True

    def schedule_activity_task(self, schedule: ScheduleActivityTaskDecisionAttributes) -> int:
        # PORT: addAllMissingVersionMarker(false, Optional.empty());
        next_decision_event_id = self.next_decision_event_id
        decision_id = DecisionId(DecisionTarget.ACTIVITY, next_decision_event_id)
        self.activity_id_to_scheduled_event_id[schedule.activity_id] = next_decision_event_id
        self.add_decision(decision_id, ActivityDecisionStateMachine(decision_id, schedule_attributes=schedule))
        return next_decision_event_id

    def complete_signal_execution(self, task: SignalMethodTask):
        task.destroy()
        self.tasks.remove(task)

    def handle_activity_task_closed(self, scheduled_event_id: int) -> bool:
        decision: DecisionStateMachine = self.get_decision(DecisionId(DecisionTarget.ACTIVITY, scheduled_event_id))
        assert decision
        decision.handle_completion_event()
        return decision.is_done()

    def handle_activity_task_scheduled(self, event: HistoryEvent):
        decision = self.get_decision(DecisionId(DecisionTarget.ACTIVITY, event.event_id))
        decision.handle_initiated_event(event)

    def handle_activity_task_started(self, event: HistoryEvent):
        attr = event.activity_task_started_event_attributes
        decision = self.get_decision(DecisionId(DecisionTarget.ACTIVITY, attr.scheduled_event_id))
        decision.handle_started_event(event)

    def handle_activity_task_completed(self, event: HistoryEvent):
        self.decision_context.handle_activity_task_completed(event)

    def handle_activity_task_failed(self, event: HistoryEvent):
        self.decision_context.handle_activity_task_failed(event)

    def handle_activity_task_timed_out(self, event: HistoryEvent):
        self.decision_context.handle_activity_task_timed_out(event)

    def handle_workflow_execution_signaled(self, event: HistoryEvent):
        signaled_event_attributes = event.workflow_execution_signaled_event_attributes
        signal_input = signaled_event_attributes.input
        if not signal_input:
            signal_input = []
        else:
            signal_input = json_to_args(signal_input)

        task = SignalMethodTask(task_id=self.execution_id,
                                workflow_instance=self.workflow_task.workflow_instance,
                                signal_name=signaled_event_attributes.signal_name,
                                signal_input=signal_input,
                                decider=self)
        self.tasks.append(task)
        task.start()

    def add_decision(self, decision_id: DecisionId, decision: DecisionStateMachine):
        self.decisions[decision_id] = decision
        self.next_decision_event_id += 1

    def get_and_increment_next_id(self) -> str:
        ret_value = str(self.id_counter)
        self.id_counter += 1
        return ret_value

    def get_decision(self, decision_id: DecisionId) -> DecisionStateMachine:
        result: DecisionStateMachine = self.decisions.get(decision_id)
        if not result:
            raise NonDeterministicWorkflowException(f"Unknown {decision_id}.")
        return result

    def get_decisions(self) -> List[Decision]:
        decisions = []
        for state_machine in self.decisions.values():
            d = state_machine.get_decision()
            if d:
                decisions.append(d)

        # PORT: // Include FORCE_IMMEDIATE_DECISION timer only if there are more then 100 events
        # PORT: int size = result.size();
        # PORT: if (size > MAXIMUM_DECISIONS_PER_COMPLETION &&
        # PORT:         !isCompletionEvent(result.get(MAXIMUM_DECISIONS_PER_COMPLETION - 2))) {
        # PORT:     result = result.subList(0, MAXIMUM_DECISIONS_PER_COMPLETION - 1);
        # PORT:     StartTimerDecisionAttributes attributes = new StartTimerDecisionAttributes();
        # PORT:     attributes.setStartToFireTimeoutSeconds(0);
        # PORT:     attributes.setTimerId(FORCE_IMMEDIATE_DECISION_TIMER);
        # PORT:     Decision d = new Decision();
        # PORT:     d.setStartTimerDecisionAttributes(attributes);
        # PORT:     d.setDecisionType(DecisionType.StartTimer);
        # PORT:     result.add(d);
        # PORT: }

        return decisions

    def destroy(self):
        if self.workflow_task:
            self.workflow_task.destroy()

    def start_timer(self, request: StartTimerDecisionAttributes):
        start_event_id = self.next_decision_event_id
        decision_id = DecisionId(DecisionTarget.TIMER, start_event_id)
        self.add_decision(decision_id, TimerDecisionStateMachine(decision_id, start_timer_attributes=request))
        return start_event_id

    def cancel_timer(self, start_event_id: int, immediate_cancellation_callback: Callable):
        decision: DecisionStateMachine = self.get_decision(DecisionId(DecisionTarget.TIMER, start_event_id))
        if decision.is_done():
            return True
        if decision.cancel(immediate_cancellation_callback):
            self.next_decision_event_id += 1
        return decision.is_done()

    def handle_timer_closed(self, attributes: TimerFiredEventAttributes) -> bool:
        decision = self.get_decision(DecisionId(DecisionTarget.TIMER, attributes.started_event_id))
        decision.handle_completion_event()
        return decision.is_done()

    def handle_timer_canceled(self, event: HistoryEvent) -> bool:
        attributes = event.timer_canceled_event_attributes
        decision = self.get_decision(DecisionId(DecisionTarget.TIMER, attributes.started_event_id))
        decision.handle_cancellation_event()
        return decision.is_done()

    def handle_cancel_timer_failed(self, event: HistoryEvent) -> bool:
        started_event_id = event.event_id
        decision = self.get_decision(DecisionId(DecisionTarget.TIMER, started_event_id))
        decision.handle_cancellation_failure_event(event)
        return decision.is_done()

    def handle_timer_started(self, event: HistoryEvent):
        decision = self.get_decision(DecisionId(DecisionTarget.TIMER, event.event_id))
        decision.handle_initiated_event(event)

    def handle_timer_fired(self, event: HistoryEvent):
        attributes = event.timer_fired_event_attributes
        self.decision_context.handle_timer_fired(attributes)

    def handle_marker_recorded(self, event: HistoryEvent):
        self.decision_context.workflow_clock.handle_marker_recorded(event)

    def get_optional_decision_event(self, event_id: int) -> HistoryEvent:
        return self.decision_events.get_optional_decision_event(event_id)

    def query(self, decision_task: PollForDecisionTaskResponse, query: WorkflowQuery) -> bytes:
        query_args = query.query_args
        if query_args is None:
            args = []
        else:
            args = json_to_args(query_args)
        task = QueryMethodTask(task_id=self.execution_id,
                               workflow_instance=self.workflow_task.workflow_instance,
                               query_name=query.query_type,
                               query_input=args,
                               decider=self)
        self.tasks.append(task)
        task.start()
        self.event_loop.run_event_loop_once()
        if task.status == Status.DONE:
            if task.exception_thrown:
                raise task.exception_thrown
            else:  # ret_value might be None, need to put it in else
                return task.ret_value
        else:
            raise QueryDidNotComplete(f"Query method {query.query_type} with args {query.query_args} did not complete")


# noinspection PyUnusedLocal
def noop(*args):
    pass


def on_timer_canceled(self: ReplayDecider, event: HistoryEvent):
    self.decision_context.handle_timer_canceled(event)


event_handlers = {
    EventType.WorkflowExecutionStarted: ReplayDecider.handle_workflow_execution_started,
    EventType.WorkflowExecutionCancelRequested: ReplayDecider.handle_workflow_execution_cancel_requested,
    EventType.WorkflowExecutionCompleted: noop,
    EventType.DecisionTaskScheduled: noop,
    EventType.DecisionTaskStarted: noop,  # Filtered by HistoryHelper
    EventType.DecisionTaskTimedOut: noop,  # TODO: check
    EventType.ActivityTaskScheduled: ReplayDecider.handle_activity_task_scheduled,
    EventType.ActivityTaskStarted: ReplayDecider.handle_activity_task_started,
    EventType.ActivityTaskCompleted: ReplayDecider.handle_activity_task_completed,
    EventType.ActivityTaskFailed: ReplayDecider.handle_activity_task_failed,
    EventType.ActivityTaskTimedOut: ReplayDecider.handle_activity_task_timed_out,
    EventType.WorkflowExecutionSignaled: ReplayDecider.handle_workflow_execution_signaled,
    EventType.TimerFired: ReplayDecider.handle_timer_fired,
    EventType.TimerStarted: ReplayDecider.handle_timer_started,
    EventType.TimerCanceled: on_timer_canceled,
    EventType.CancelTimerFailed: ReplayDecider.handle_cancel_timer_failed,
    EventType.MarkerRecorded: ReplayDecider.handle_marker_recorded
}


@dataclass
class DecisionTaskLoop:
    worker: Worker
    service: WorkflowService = None
    deciders: Dict[str, ReplayDecider] = field(default_factory=dict)

    def __post_init__(self):
        pass

    def start(self):
        thread = threading.Thread(target=self.run)
        thread.start()

    def run(self):
        try:
            logger.info(f"Decision task worker started: {WorkflowService.get_identity()}")
            event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(event_loop)
            self.service = WorkflowService.create(self.worker.host, self.worker.port)
            self.worker.manage_service(self.service)
            while True:
                if self.worker.is_stop_requested():
                    return
                decision_task: PollForDecisionTaskResponse = self.poll()
                if not decision_task:
                    continue
                if decision_task.query:
                    try:
                        result = self.process_query(decision_task)
                        self.respond_query(decision_task.task_token, result, None)
                    except Exception as ex:
                        logger.error("Error")
                        self.respond_query(decision_task.task_token, None, serialize_exception(ex))
                else:
                    decisions = self.process_task(decision_task)
                    self.respond_decisions(decision_task.task_token, decisions)
        finally:
            # noinspection PyPep8,PyBroadException
            try:
                self.service.close()
            except:
                logger.warning("service.close() failed", exc_info=1)
            self.worker.notify_thread_stopped()

    def poll(self) -> Optional[PollForDecisionTaskResponse]:
        try:
            polling_start = datetime.datetime.now()
            poll_decision_request = PollForDecisionTaskRequest()
            poll_decision_request.identity = WorkflowService.get_identity()
            poll_decision_request.task_list = TaskList()
            poll_decision_request.task_list.name = self.worker.task_list
            poll_decision_request.domain = self.worker.domain
            # noinspection PyUnusedLocal
            task: PollForDecisionTaskResponse
            task, err = self.service.poll_for_decision_task(poll_decision_request)
            polling_end = datetime.datetime.now()
            logger.debug("PollForDecisionTask: %dms", (polling_end - polling_start).total_seconds() * 1000)
        except TChannelException as ex:
            logger.error("PollForDecisionTask error: %s", ex)
            return None
        if err:
            logger.error("PollForDecisionTask failed: %s", err)
            return None
        if not task.task_token:
            logger.debug("PollForActivityTask has no task token (expected): %s", task)
            return None
        return task

    def process_task(self, decision_task: PollForDecisionTaskResponse) -> List[Decision]:
        execution_id = str(decision_task.workflow_execution)
        decider = ReplayDecider(execution_id, decision_task.workflow_type, self.worker)
        decisions: List[Decision] = decider.decide(decision_task.history.events)
        decider.destroy()
        return decisions

    def process_query(self, decision_task: PollForDecisionTaskResponse) -> bytes:
        execution_id = str(decision_task.workflow_execution)
        decider = ReplayDecider(execution_id, decision_task.workflow_type, self.worker)
        decider.decide(decision_task.history.events)
        try:
            result = decider.query(decision_task, decision_task.query)
            return json.dumps(result)
        finally:
            decider.destroy()

    def respond_query(self, task_token: bytes, result: bytes = None, error_message: str = None):
        service = self.service
        request = RespondQueryTaskCompletedRequest()
        request.task_token = task_token
        if result:
            request.query_result = result
            request.completed_type = QueryTaskCompletedType.COMPLETED
        else:
            request.error_message = error_message
            request.completed_type = QueryTaskCompletedType.FAILED
        _, err = service.respond_query_task_completed(request)
        if err:
            logger.error("Error invoking RespondDecisionTaskCompleted: %s", err)
        else:
            logger.debug("RespondQueryTaskCompleted successful")

    def respond_decisions(self, task_token: bytes, decisions: List[Decision]):
        service = self.service
        request = RespondDecisionTaskCompletedRequest()
        request.task_token = task_token
        request.decisions.extend(decisions)
        request.identity = WorkflowService.get_identity()
        # noinspection PyUnusedLocal
        response: RespondDecisionTaskCompletedResponse
        response, err = service.respond_decision_task_completed(request)
        if err:
            logger.error("Error invoking RespondDecisionTaskCompleted: %s", err)
        else:
            logger.debug("RespondDecisionTaskCompleted: %s", response)


from cadence.clock_decision_context import ClockDecisionContext, TimerCancellationHandler, LOCAL_ACTIVITY_MARKER_NAME
from cadence.replay_interceptor import make_replay_aware
