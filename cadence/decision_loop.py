from __future__ import annotations

import asyncio
import contextvars
import datetime
import json
import logging
import threading
from asyncio import Task
from asyncio.base_futures import CancelledError
from asyncio.events import AbstractEventLoop
from asyncio.futures import Future
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any

from more_itertools import peekable

from cadence.activity_method import ExecuteActivityParameters
from cadence.cadence_types import PollForDecisionTaskRequest, TaskList, PollForDecisionTaskResponse, \
    RespondDecisionTaskCompletedRequest, \
    CompleteWorkflowExecutionDecisionAttributes, Decision, DecisionType, RespondDecisionTaskCompletedResponse, \
    HistoryEvent, EventType, WorkflowType, ScheduleActivityTaskDecisionAttributes
from cadence.decisions import DecisionId, DecisionTarget
from cadence.exceptions import WorkflowTypeNotFound, NonDeterministicWorkflowException, ActivityTaskFailedException, \
    ActivityTaskTimeoutException
from cadence.state_machines import ActivityDecisionStateMachine, DecisionStateMachine, CompleteWorkflowStateMachine
from cadence.tchannel import TChannelException
from cadence.worker import Worker
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
        result = DecisionEvents(new_events, decision_events, replay, next_decision_event_id)
        logger.debug("HistoryHelper next=%s", result)
        return result


@dataclass
class DecisionEvents:
    events: List[HistoryEvent]
    decision_events: List[HistoryEvent]
    replay: bool
    next_decision_event_id: int


class Status(Enum):
    CREATED = 1
    RUNNING = 2
    DONE = 3


current_workflow_task = contextvars.ContextVar("current_workflow_task")


@dataclass
class WorkflowTask:
    task_id: str
    workflow_input: List
    worker: Worker
    workflow_type: WorkflowType
    decider: ReplayDecider
    status: Status = Status.CREATED
    workflow_instance: object = None
    ret_value: object = None
    exception_thrown: BaseException = None
    task: Task = None

    @staticmethod
    def current() -> WorkflowTask:
        return current_workflow_task.get()

    def __post_init__(self):
        logger.debug(f"[task-{self.task_id}] Created")
        self.task = asyncio.get_event_loop().create_task(self.workflow_main())

    async def workflow_main(self):
        logger.debug(f"[task-{self.task_id}] Running")
        current_workflow_task.set(self)

        if self.workflow_type.name not in self.worker.workflow_methods:
            self.status = Status.DONE
            self.exception_thrown = WorkflowTypeNotFound(self.workflow_type.name)
            logger.error(f"Workflow type not found: {self.workflow_type.name}")
            return

        cls, workflow_proc = self.worker.workflow_methods[self.workflow_type.name]
        self.status = Status.RUNNING
        try:
            logger.info(f"Invoking workflow {self.workflow_type.name}({str(self.workflow_input)[1:-1]})")
            self.workflow_instance = cls()
            self.ret_value = await workflow_proc(self.workflow_instance, *self.workflow_input)
            logger.info(
                f"Workflow {self.workflow_type.name}({str(self.workflow_input)[1:-1]}) returned {self.ret_value}")
            self.decider.complete_workflow_execution(self.ret_value)
        except CancelledError:
            logger.debug("Coroutine cancelled (expected)")
        except Exception as ex:
            logger.error(
                f"Workflow {self.workflow_type.name}({str(self.workflow_input)[1:-1]}) failed", exc_info=1)
            self.exception_thrown = ex
        finally:
            self.status = Status.DONE

    def is_done(self):
        return self.status == Status.DONE

    def destroy(self):
        if self.status == Status.RUNNING:
            self.status = Status.DONE
            self.task.cancel()


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

        # PORT: RetryParameters retryParameters = parameters.getRetryParameters();
        # PORT: if (retryParameters != null) {
        # PORT:    attributes.setRetryPolicy(retryParameters.toRetryPolicy());
        # PORT: }

        scheduled_event_id = self.decider.schedule_activity_task(schedule=attr)
        future = self.decider.event_loop.create_future()
        self.scheduled_activities[scheduled_event_id] = future
        await future
        assert future.done()
        exception = future.exception()
        if exception:
            raise exception
        raw_bytes = future.result()
        return json.loads(str(raw_bytes, "utf-8"))

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
                ex = ActivityTaskFailedException(attr.reason, attr.details)
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


@dataclass
class ReplayDecider:
    execution_id: str
    workflow_type: WorkflowType
    worker: Worker
    workflow_task: WorkflowTask = None
    event_loop: EventLoopWrapper = field(default_factory=EventLoopWrapper)

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
        self.handle_decision_task_started(decision_events)
        for event in decision_events.events:
            self.process_event(event)
        self.event_loop.run_event_loop_once()
        if decision_events.replay:
            self.notify_decision_sent()
        for event in decision_events.decision_events:
            self.process_event(event)

    def process_event(self, event: HistoryEvent):
        event_handler = event_handlers.get(event.event_type)
        if not event_handler:
            raise Exception(f"No event handler for event type {event.event_type.name}")
        event_handler(self, event)

    def handle_workflow_execution_started(self, event: HistoryEvent):
        start_event_attributes = event.workflow_execution_started_event_attributes
        if start_event_attributes.input is None:
            workflow_input = []
        else:
            workflow_input = json.loads(start_event_attributes.input)
            if not isinstance(workflow_input, list):
                workflow_input = [workflow_input]
        self.workflow_task = WorkflowTask(task_id=self.execution_id, workflow_input=workflow_input,
                                          worker=self.worker, workflow_type=self.workflow_type, decider=self)

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

    def schedule_activity_task(self, schedule: ScheduleActivityTaskDecisionAttributes) -> int:
        # PORT: addAllMissingVersionMarker(false, Optional.empty());
        next_decision_event_id = self.next_decision_event_id
        decision_id = DecisionId(DecisionTarget.ACTIVITY, next_decision_event_id)
        self.activity_id_to_scheduled_event_id[schedule.activity_id] = next_decision_event_id
        self.add_decision(decision_id, ActivityDecisionStateMachine(decision_id, schedule_attributes=schedule))
        return next_decision_event_id

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


# noinspection PyUnusedLocal
def noop(*args):
    pass


event_handlers = {
    EventType.WorkflowExecutionStarted: ReplayDecider.handle_workflow_execution_started,
    EventType.DecisionTaskScheduled: noop,
    EventType.DecisionTaskStarted: noop,  # Filtered by HistoryHelper
    EventType.DecisionTaskTimedOut: noop,  # TODO: check
    EventType.ActivityTaskScheduled: ReplayDecider.handle_activity_task_scheduled,
    EventType.ActivityTaskStarted: ReplayDecider.handle_activity_task_started,
    EventType.ActivityTaskCompleted: ReplayDecider.handle_activity_task_completed,
    EventType.ActivityTaskFailed: ReplayDecider.handle_activity_task_failed,
    EventType.ActivityTaskTimedOut: ReplayDecider.handle_activity_task_timed_out
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
            while True:
                if self.worker.is_stop_requested():
                    return
                decision_task: PollForDecisionTaskResponse = self.poll()
                if not decision_task:
                    continue
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
