import copy
import inspect
import json
from dataclasses import dataclass
from typing import Callable, List

from cadence.cadence_types import ActivityType
from cadence.conversions import args_to_json


def get_activity_method_name(method: Callable):
    return "::".join(method.__qualname__.split(".")[-2:])


@dataclass
class RetryParameters:
    initial_interval_in_seconds: int
    backoff_coefficient: float
    maximum_interval_in_seconds: int
    maximum_attempts: int
    non_retriable_error_reasons: List[str]
    expiration_interval_in_seconds: int


@dataclass
class ExecuteActivityParameters:
    activity_id: str = ""
    activity_type: ActivityType = None
    heartbeat_timeout_seconds: int = 0
    input: bytes = None
    schedule_to_close_timeout_seconds: int = 0
    schedule_to_start_timeout_seconds: int = 0
    start_to_close_timeout_seconds: int = 0
    task_list: str = ""
    retry_parameters: RetryParameters = None


def activity_method(func: Callable = None, name: str = "", schedule_to_close_timeout_seconds: int = 0,
                    schedule_to_start_timeout_seconds: int = 0, start_to_close_timeout_seconds: int = 0,
                    heartbeat_timeout_seconds: int = 0, task_list: str = ""):
    def wrapper(fn: Callable):
        # noinspection PyProtectedMember
        async def stub_activity_fn(self, *args):
            assert self._decision_context
            assert stub_activity_fn._execute_parameters
            parameters = copy.deepcopy(stub_activity_fn._execute_parameters)
            parameters.input = args_to_json(args).encode("utf-8")
            from cadence.decision_loop import DecisionContext
            decision_context: DecisionContext = self._decision_context
            return await decision_context.schedule_activity_task(parameters=parameters)

        if not task_list:
            raise Exception("task_list parameter is mandatory")

        execute_parameters = ExecuteActivityParameters()
        execute_parameters.activity_type = ActivityType()
        execute_parameters.activity_type.name = name if name else get_activity_method_name(fn)
        execute_parameters.schedule_to_close_timeout_seconds = schedule_to_close_timeout_seconds
        execute_parameters.schedule_to_start_timeout_seconds = schedule_to_start_timeout_seconds
        execute_parameters.start_to_close_timeout_seconds = start_to_close_timeout_seconds
        execute_parameters.heartbeat_timeout_seconds = heartbeat_timeout_seconds
        execute_parameters.task_list = task_list
        stub_activity_fn._execute_parameters = execute_parameters
        return stub_activity_fn

    if func and inspect.isfunction(func):
        raise Exception("activity_method must be called with arguments")
    else:
        return wrapper
