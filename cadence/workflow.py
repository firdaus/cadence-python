from __future__ import annotations
import datetime
import inspect
import json
import random
import uuid
from dataclasses import dataclass, field
from typing import Callable, List, Type, Dict, Tuple
from uuid import uuid4

from cadence.cadence_types import WorkflowIdReusePolicy, StartWorkflowExecutionRequest, TaskList, WorkflowType, \
    GetWorkflowExecutionHistoryRequest, WorkflowExecution, HistoryEventFilterType, EventType, HistoryEvent, \
    StartWorkflowExecutionResponse, SignalWorkflowExecutionRequest
from cadence.conversions import args_to_json
from cadence.workflowservice import WorkflowService


class Workflow:

    @staticmethod
    def new_activity_stub(activities_cls):
        from cadence.decision_loop import ITask
        task: ITask = ITask.current()
        assert task
        cls = activities_cls()
        cls._decision_context = task.decider.decision_context
        return cls

    @staticmethod
    async def await_till(c: Callable, timeout_seconds: int = 0) -> bool:
        from cadence.decision_loop import ITask
        task: ITask = ITask.current()
        assert task
        return await task.await_till(c, timeout_seconds)

    @staticmethod
    async def sleep(seconds: int):
        from cadence.decision_loop import ITask
        task: ITask = ITask.current()
        await task.decider.decision_context.schedule_timer(seconds)

    @staticmethod
    def current_time_millis() -> int:
        from cadence.decision_loop import ITask
        task: ITask = ITask.current()
        return task.decider.decision_context.current_time_millis()

    @staticmethod
    def now() -> datetime.datetime:
        from cadence.decision_loop import ITask
        task: ITask = ITask.current()
        now_in_ms = task.decider.decision_context.current_time_millis()
        return datetime.datetime.fromtimestamp(now_in_ms / 1000)

    @staticmethod
    def random_uuid() -> uuid.UUID:
        from cadence.decision_loop import ITask
        task: ITask = ITask.current()
        return task.decider.decision_context.random_uuid()

    @staticmethod
    def new_random() -> random.Random:
        from cadence.decision_loop import ITask
        task: ITask = ITask.current()
        return task.decider.decision_context.new_random()

class WorkflowStub:
    pass


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

    @classmethod
    def start(cls, stub_fn: Callable, *args) -> WorkflowExecution:
        stub = stub_fn.__self__
        assert stub._workflow_client is not None
        assert stub_fn._workflow_method is not None
        return exec_workflow(stub._workflow_client, stub_fn._workflow_method, args, workflow_options=stub._workflow_options, stub_instance=stub)

    def new_workflow_stub(self, cls: Type, workflow_options: WorkflowOptions = None):
        attrs = {}
        attrs["_workflow_client"] = self
        attrs["_workflow_options"] = workflow_options
        for name, fn in inspect.getmembers(cls, inspect.isfunction):
            if hasattr(fn, "_workflow_method"):
                attrs[name] = get_workflow_stub_fn(fn._workflow_method)
            elif hasattr(fn, "_signal_method"):
                attrs[name] = get_signal_stub_fn(fn._signal_method)
        stub_cls = type(cls.__name__, (WorkflowStub,), attrs)
        return stub_cls()

    def wait_for_close(self, execution: WorkflowExecution) -> object:
        while True:
            history_request = create_close_history_event_request(self, execution.workflow_id, execution.run_id)
            history_response, err = self.service.get_workflow_execution_history(history_request)
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
            elif history_event.event_type == EventType.WorkflowExecutionCanceled:
                raise WorkflowExecutionCanceledException()
            else:
                raise Exception("Unexpected history close event: " + str(history_event))


def exec_workflow(workflow_client, wm: WorkflowMethod, args, workflow_options: WorkflowOptions = None, stub_instance: object = None) -> WorkflowExecution:
    start_request = create_start_workflow_request(workflow_client, wm, args)
    start_response, err = workflow_client.service.start_workflow(start_request)
    if err:
        raise Exception(err)
    execution = WorkflowExecution(workflow_id=start_request.workflow_id, run_id=start_response.run_id)
    stub_instance._execution = execution
    return execution


def exec_workflow_sync(workflow_client: WorkflowClient, wm: WorkflowMethod, args: List,
                       workflow_options: WorkflowOptions = None, stub_instance: object = None):
    execution: WorkflowExecution = exec_workflow(workflow_client, wm, args, workflow_options=workflow_options, stub_instance=stub_instance)
    return workflow_client.wait_for_close(execution)


def exec_signal(workflow_client: WorkflowClient, sm: SignalMethod, args, stub_instance: object = None):
    assert stub_instance._execution
    request = SignalWorkflowExecutionRequest()
    request.workflow_execution = stub_instance._execution
    request.signal_name = sm.name
    request.input = args_to_json(args)
    request.domain = workflow_client.domain
    response, err = workflow_client.service.signal_workflow_execution(request)
    if err:
        raise Exception(err)


def create_start_workflow_request(workflow_client: WorkflowClient, wm: WorkflowMethod,
                                  args: List) -> StartWorkflowExecutionRequest:
    start_request = StartWorkflowExecutionRequest()
    start_request.domain = workflow_client.domain
    start_request.workflow_id = wm._workflow_id if wm._workflow_id else str(uuid4())
    start_request.workflow_type = WorkflowType()
    start_request.workflow_type.name = wm._name
    start_request.task_list = TaskList()
    start_request.task_list.name = wm._task_list
    start_request.input = args_to_json(args)
    start_request.execution_start_to_close_timeout_seconds = wm._execution_start_to_close_timeout_seconds
    start_request.task_start_to_close_timeout_seconds = wm._task_start_to_close_timeout_seconds
    start_request.identity = workflow_client.service.get_identity()
    start_request.workflow_id_reuse_policy = wm._workflow_id_reuse_policy
    start_request.request_id = str(uuid4())
    start_request.cron_schedule = wm._cron_schedule if wm._cron_schedule else None
    return start_request


def create_close_history_event_request(workflow_client: WorkflowClient, workflow_id: str,
                                       run_id: str) -> GetWorkflowExecutionHistoryRequest:
    history_request = GetWorkflowExecutionHistoryRequest()
    history_request.domain = workflow_client.domain
    history_request.execution = WorkflowExecution()
    history_request.execution.workflow_id = workflow_id
    history_request.execution.run_id = run_id
    history_request.wait_for_new_event = True
    history_request.history_event_filter_type = HistoryEventFilterType.CLOSE_EVENT
    return history_request


def get_workflow_method_name(method):
    return "::".join(method.__qualname__.split(".")[-2:])


def get_workflow_stub_fn(wm: WorkflowMethod):
    def workflow_stub_fn(self, *args):
        assert self._workflow_client is not None
        return exec_workflow_sync(self._workflow_client, wm, args,
                                  workflow_options=self._workflow_options, stub_instance=self)
    workflow_stub_fn._workflow_method = wm
    return workflow_stub_fn


def get_signal_stub_fn(sm: SignalMethod):
    def signal_stub_fn(self, *args):
        assert self._workflow_client is not None
        return exec_signal(self._workflow_client, sm, args, stub_instance=self)
    signal_stub_fn._signal_method = sm
    return signal_stub_fn

@dataclass
class WorkflowMethod(object):
    _name: str = None
    _workflow_id: str = None
    _workflow_id_reuse_policy: WorkflowIdReusePolicy = None
    _execution_start_to_close_timeout_seconds: int = None
    _task_start_to_close_timeout_seconds: int = None
    _task_list: str = None
    _cron_schedule: str = None


def workflow_method(func=None,
                    name=None,
                    workflow_id=None,
                    workflow_id_reuse_policy=WorkflowIdReusePolicy.AllowDuplicateFailedOnly,
                    execution_start_to_close_timeout_seconds=7200,  # (2 hours)
                    task_start_to_close_timeout_seconds=10,  # same timeout as Java library
                    task_list=None):
    def wrapper(fn):
        if not hasattr(fn, "_workflow_method"):
            fn._workflow_method = WorkflowMethod()
        fn._workflow_method._name = name if name else get_workflow_method_name(fn)
        fn._workflow_method._workflow_id = workflow_id
        fn._workflow_method._workflow_id_reuse_policy = workflow_id_reuse_policy
        fn._workflow_method._execution_start_to_close_timeout_seconds = execution_start_to_close_timeout_seconds
        fn._workflow_method._task_start_to_close_timeout_seconds = task_start_to_close_timeout_seconds
        fn._workflow_method._task_list = task_list
        return fn
    if func and inspect.isfunction(func):
        return wrapper(func)
    else:
        return wrapper


@dataclass
class SignalMethod:
    name: str = None


def signal_method(func=None, name: str = None):
    def wrapper(fn):
        fn._signal_method = SignalMethod()
        fn._signal_method.name = name if name else get_workflow_method_name(fn)
        return fn
    if func and inspect.isfunction(func):
        return wrapper(func)
    else:
        return wrapper


def cron_schedule(value):
    def wrapper(fn):
        if not hasattr(fn, "_workflow_method"):
            fn._workflow_method = WorkflowMethod()
        fn._workflow_method._cron_schedule = value
        return fn
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
class WorkflowExecutionCanceledException(Exception):
    pass


@dataclass
class WorkflowExecutionTerminatedException(Exception):
    reason: str
    details: object
    identity: str

    def __str__(self) -> str:
        return self.reason
