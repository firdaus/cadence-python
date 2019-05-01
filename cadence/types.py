from dataclasses import dataclass
import typing
import re


PRIMITIVES = [int, str, bytes]


@dataclass
class WorkflowExecution:
    workflow_id: str = None
    run_id: str = None


@dataclass
class ActivityType:
    name: str = None


@dataclass
class WorkflowType:
    name: str = None


@dataclass
class PollForActivityTaskResponse:
    task_token: bytes = None
    workflow_execution: WorkflowExecution = None
    activity_id: str = None
    activity_type: ActivityType = None
    input: bytes = None
    scheduled_timestamp: int = None
    schedule_to_close_timeout_seconds: int = None
    started_timestamp: int = None
    start_to_close_timeout_seconds: int = None
    heartbeat_timeout_seconds: int = None
    attempt: int = None
    scheduled_timestamp_of_this_attempt: int = None
    heartbeat_details: bytes = None
    workflow_type: WorkflowType = None
    workflow_domain: str = None


def camel_to_snake(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def copy_thrift_to_py(thrift_object, python_cls):
    hints = typing.get_type_hints(python_cls)
    obj = python_cls()
    for thrift_field in dir(thrift_object):
        python_field = camel_to_snake(thrift_field)
        if python_field not in hints:
            continue
        field_type = hints[python_field]
        value = getattr(thrift_object, thrift_field)
        if field_type in PRIMITIVES:
            setattr(obj, python_field, value)
        else:
            setattr(obj, python_field, copy_thrift_to_py(value, field_type))
    return obj
