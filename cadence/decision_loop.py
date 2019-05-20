from __future__ import annotations

import asyncio
import contextvars
import datetime
import json
import logging
import threading
from asyncio import Task
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional

from more_itertools import peekable

from cadence.cadence_types import PollForDecisionTaskRequest, TaskList, PollForDecisionTaskResponse, \
    RespondDecisionTaskCompletedRequest, \
    CompleteWorkflowExecutionDecisionAttributes, Decision, DecisionType, RespondDecisionTaskCompletedResponse, \
    HistoryEvent, EventType, WorkflowType
from cadence.decisions import DecisionId
from cadence.exceptions import WorkflowTypeNotFound
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
    decision_context: DecisionContext
    status: Status = Status.CREATED
    workflow_instance: object = None
    ret_value: object = None
    exception_thrown: BaseException = None
    task: Task = None

    @staticmethod
    def current():
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
            self.decision_context.complete_workflow(self.ret_value)
        except BaseException as ex:
            logger.error(
                f"Workflow {self.workflow_type.name}({str(self.workflow_input)[1:-1]}) failed", exc_info=1)
            self.exception_thrown = ex
        finally:
            self.status = Status.DONE

    def is_done(self):
        return self.status == Status.DONE

    def destroy(self):
        self.status = Status.DONE
        self.task.cancel()


def run_event_loop_once():
    event_loop = asyncio.get_event_loop()
    event_loop.call_soon(event_loop.stop)
    event_loop.run_forever()


@dataclass
class DecisionContext:
    execution_id: str
    workflow_type: WorkflowType
    worker: Worker
    workflow_task: WorkflowTask = None
    decisions: List[Decision] = field(default_factory=list)

    def decide(self, events: List[HistoryEvent]):
        helper = HistoryHelper(events)
        while helper.has_next():
            decision_events = helper.next()
            for event in decision_events.events:
                self.process_event(event)
            run_event_loop_once()
            for event in decision_events.decision_events:
                self.process_event(event)
        return self.get_decisions()

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
                                          worker=self.worker, workflow_type=self.workflow_type, decision_context=self)

    def complete_workflow(self, ret_value):
        attr = CompleteWorkflowExecutionDecisionAttributes()
        attr.result = json.dumps(ret_value)
        decision = Decision()
        decision.decision_type = DecisionType.CompleteWorkflowExecution
        decision.complete_workflow_execution_decision_attributes = attr
        self.decisions.append(decision)

    def get_decisions(self) -> List[Decision]:
        decisions = self.decisions.copy()
        self.decisions.clear()
        return decisions


# noinspection PyUnusedLocal
def noop(*args):
    pass


event_handlers = {
    EventType.WorkflowExecutionStarted: DecisionContext.handle_workflow_execution_started,
    EventType.DecisionTaskScheduled: noop,
    EventType.DecisionTaskStarted: noop,  # Filtered by HistoryHelper
    EventType.ActivityTaskScheduled: None,
    EventType.ActivityTaskStarted: None,
    EventType.ActivityTaskCompleted: None
}


@dataclass
class DecisionTaskLoop:
    worker: Worker
    service: WorkflowService = None
    decision_contexts: Dict[str, DecisionContext] = field(default_factory=dict)

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
            try:
                self.service.close()
            except:
                pass
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
        decision_context = DecisionContext(execution_id, decision_task.workflow_type, self.worker)
        return decision_context.decide(decision_task.history.events)

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