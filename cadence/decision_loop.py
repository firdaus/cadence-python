from __future__ import annotations

import datetime
import json
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional

from more_itertools import peekable

from cadence.cadence_types import PollForDecisionTaskRequest, TaskList, PollForDecisionTaskResponse, \
    RespondDecisionTaskCompletedRequest, \
    CompleteWorkflowExecutionDecisionAttributes, Decision, DecisionType, RespondDecisionTaskCompletedResponse, \
    HistoryEvent, EventType
from cadence.tchannel import TChannelException
from cadence.worker import Worker
from cadence.workflow import Workflow
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


def one_iteration(worker: Worker, service: WorkflowService):
    try:
        polling_start = datetime.datetime.now()
        poll_decision_request = PollForDecisionTaskRequest()
        poll_decision_request.identity = WorkflowService.get_identity()
        poll_decision_request.task_list = TaskList()
        poll_decision_request.task_list.name = worker.task_list
        poll_decision_request.domain = worker.domain
        task: PollForDecisionTaskResponse
        task, err = service.poll_for_decision_task(poll_decision_request)
        polling_end = datetime.datetime.now()
        logger.debug("PollForDecisionTask: %dms", (polling_end - polling_start).total_seconds() * 1000)
    except TChannelException as ex:
        logger.error("PollForDecisionTask error: %s", ex)
        return
    if err:
        logger.error("PollForDecisionTask failed: %s", err)
        return
    if not task.task_token:
        logger.debug("PollForActivityTask has no task token (expected): %s", task)
        return
    if task.workflow_type.name not in worker.workflow_methods:
        logger.error(f"Workflow type not found: {task.workflow_type.name}")
        return
    cls, fn = worker.workflow_methods[task.workflow_type.name]
    workflow = Workflow(task.history.events)
    workflow_instance = cls(workflow=workflow)
    start_history_event = workflow.history.pop(0)
    start_event_attributes = start_history_event.workflow_execution_started_event_attributes
    workflow_input = json.loads(start_event_attributes.input)
    if not isinstance(workflow_input, list):
        workflow_input = [workflow_input]
    logger.info(f"Invoking workflow {task.workflow_type.name}({str(workflow_input)[1:-1]})")
    ret_value = fn(workflow_instance, *workflow_input)
    logger.info(f"Workflow {task.workflow_type.name}({str(workflow_input)[1:-1]}) returned {ret_value}")
    complete_workflow(service, task.task_token, ret_value)


def complete_workflow(service: WorkflowService, task_token: str, ret_value):
    request = RespondDecisionTaskCompletedRequest()
    request.task_token = task_token
    attr = CompleteWorkflowExecutionDecisionAttributes()
    attr.result = json.dumps(ret_value)
    decision = Decision()
    decision.decision_type = DecisionType.CompleteWorkflowExecution
    decision.complete_workflow_execution_decision_attributes = attr
    request.decisions.append(decision)
    request.identity = WorkflowService.get_identity()
    response: RespondDecisionTaskCompletedResponse
    response, err = service.respond_decision_task_completed(request)
    if err:
        logger.error("Error invoking RespondDecisionTaskCompleted: %s", err)
    else:
        logger.debug("RespondDecisionTaskCompleted: %s", response)


def decision_task_loop(worker: Worker):
    service = WorkflowService.create(worker.host, worker.port)
    logger.info(f"Decision task worker started: {WorkflowService.get_identity()}")
    while True:
        one_iteration(worker, service)
