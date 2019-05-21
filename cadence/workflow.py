from __future__ import annotations
import inspect
import json
from dataclasses import dataclass, field
from typing import Callable, List, Type, Dict
from uuid import uuid4

from cadence.cadence_types import WorkflowIdReusePolicy, StartWorkflowExecutionRequest, TaskList, WorkflowType, \
    GetWorkflowExecutionHistoryRequest, WorkflowExecution, HistoryEventFilterType, EventType, HistoryEvent
from cadence.workflowservice import WorkflowService


class Workflow:

    @staticmethod
    def new_activity_stub(activities_cls):
        from cadence.decision_loop import WorkflowTask
        task = WorkflowTask.current()
        assert task
        cls = activities_cls()
        cls._decision_context = task.decider.decision_context
        return cls


@dataclass
class WorkflowClient:
    service: WorkflowService
    domain: domain
    options: WorkflowClientOptions

    @classmethod
    def new_client(cls, host: str = "localhost", port: int = 7933, domain: str = "",
                   options: WorkflowClientOptions = None) -> WorkflowClient:
        service = WorkflowService.create(host, port)
        return cls(service=service, domain=domain, options=options)

    def new_workflow_stub(self, cls: Type, workflow_options: WorkflowOptions = None):
        stub = cls()
        stub._workflow_client = self
        stub._workflow_options = workflow_options
        return stub


def exec_workflow_sync(workflow_client: WorkflowClient, stub_fn: Callable, args: List,
                       workflow_options: WorkflowOptions = None):
    start_request = create_start_workflow_request(workflow_client, stub_fn, args)
    start_response, err = workflow_client.service.start_workflow(start_request)
    if err:
        raise Exception(err)
    while True:
        workflow_id = start_request.workflow_id
        run_id = start_response.run_id
        history_request = create_close_history_event_request(workflow_client, workflow_id, run_id)
        history_response, err = workflow_client.service.get_workflow_execution_history(history_request)
        if err:
            raise Exception(err)
        if not history_response.history.events:
            continue
        history_event = history_response.history.events[0]
        if history_event.event_type == EventType.WorkflowExecutionCompleted:
            attributes = history_event.workflow_execution_completed_event_attributes
            return json.loads(attributes.result)
        elif history_event.event_type == EventType.WorkflowExecutionFailed:
            attributes = history_event.workflow_execution_failed_event_attributes
            details: Dict = json.loads(attributes.details)
            detail_message = details.get("detailMessage", "")
            raise WorkflowExecutionFailedException(attributes.reason, details=details, detail_message=detail_message)
        elif history_event.event_type == EventType.WorkflowExecutionTimedOut:
            raise WorkflowExecutionTimedOutException()
        elif history_event.event_type == EventType.WorkflowExecutionTerminated:
            attributes = history_event.workflow_execution_terminated_event_attributes
            raise WorkflowExecutionTerminatedException(reason=attributes.reason, details=attributes.details,
                                                       identity=attributes.identity)
        else:
            raise Exception("Unexpected history close event: " + str(history_event))


def create_start_workflow_request(workflow_client: WorkflowClient, stub_fn: object,
                                  args: List) -> StartWorkflowExecutionRequest:
    start_request = StartWorkflowExecutionRequest()
    start_request.domain = workflow_client.domain
    start_request.workflow_id = stub_fn._workflow_id if stub_fn._workflow_id else str(uuid4())
    start_request.workflow_type = WorkflowType()
    start_request.workflow_type.name = stub_fn._name
    start_request.task_list = TaskList()
    start_request.task_list.name = stub_fn._task_list
    start_request.input = json.dumps(args)
    start_request.execution_start_to_close_timeout_seconds = stub_fn._execution_start_to_close_timeout_seconds
    start_request.task_start_to_close_timeout_seconds = stub_fn._task_start_to_close_timeout_seconds
    start_request.identity = workflow_client.service.get_identity()
    start_request.workflow_id_reuse_policy = stub_fn._workflow_id_reuse_policy
    start_request.request_id = str(uuid4())
    return start_request


def create_close_history_event_request(workflow_client: WorkflowClient, workflow_id: str,
                                       run_id: str) -> GetWorkflowExecutionHistoryRequest:
    history_request = GetWorkflowExecutionHistoryRequest()
    history_request.domain = workflow_client.domain
    history_request.execution = WorkflowExecution()
    history_request.execution.workflow_id = workflow_id
    history_request.execution.run_id = run_id
    history_request.maximum_page_size = 1
    history_request.wait_for_new_event = True
    history_request.history_event_filter_type = HistoryEventFilterType.CLOSE_EVENT
    return history_request


def get_workflow_method_name(method):
    return "::".join(method.__qualname__.split(".")[-2:])


def workflow_method(func=None,
                    name=None,
                    workflow_id=None,
                    workflow_id_reuse_policy=WorkflowIdReusePolicy.AllowDuplicateFailedOnly,
                    execution_start_to_close_timeout_seconds=7200,  # (2 hours)
                    task_start_to_close_timeout_seconds=10,  # same timeout as Java library
                    task_list=None,
                    impl=False):
    def wrapper(fn):
        if impl:
            async def stub_fn(self, *args):
                return await fn(self, *args)
        else:
            def stub_fn(self, *args):
                assert self._workflow_client is not None
                return exec_workflow_sync(self._workflow_client, stub_fn, args,
                                          workflow_options=self._workflow_options)

        stub_fn._workflow_method = True
        stub_fn._name = name if name else get_workflow_method_name(fn)
        stub_fn._workflow_id = workflow_id
        stub_fn._workflow_id_reuse_policy = workflow_id_reuse_policy
        stub_fn._execution_start_to_close_timeout_seconds = execution_start_to_close_timeout_seconds
        stub_fn._task_start_to_close_timeout_seconds = task_start_to_close_timeout_seconds
        stub_fn._task_list = task_list
        return stub_fn

    if func and inspect.isfunction(func):
        return wrapper(func)
    else:
        return wrapper


@dataclass
class WorkflowClientOptions:
    pass


@dataclass
class WorkflowOptions:
    pass


@dataclass
class WorkflowExecutionFailedException(Exception):
    reason: str
    details: Dict[str, str]
    detail_message: str

    def __str__(self) -> str:
        cause = self.details.get("cause")
        if cause:
            return f"{cause['class']}: {cause['detailMessage']}"
        else:
            return f"{self.reason}: {self.detail_message}"


@dataclass
class WorkflowExecutionTimedOutException(Exception):
    pass


@dataclass
class WorkflowExecutionTerminatedException(Exception):
    reason: str
    details: object
    identity: str

    def __str__(self) -> str:
        return self.reason
