from __future__ import annotations

from typing import Tuple
from uuid import uuid4

import os
import socket

from cadence.thrift import cadence
from cadence.connection import TChannelConnection, ThriftFunctionCall
from cadence.errors import find_error
from cadence.conversions import copy_thrift_to_py, copy_py_to_thrift
from cadence.types import PollForActivityTaskResponse, StartWorkflowExecutionRequest, StartWorkflowExecutionResponse, \
    RegisterDomainRequest, PollForActivityTaskRequest

TCHANNEL_SERVICE = "cadence-frontend"


class WorkflowService:

    @classmethod
    def create(cls, host: str, port: int):
        connection = TChannelConnection.open(host, port)
        return cls(connection)

    @classmethod
    def get_identity(self):
        return "%d@%s" % (os.getpid(), socket.gethostname())

    def __init__(self, connection: TChannelConnection):
        self.connection = connection
        self.execution_start_to_close_timeout_seconds = 86400
        self.task_start_to_close_timeout_seconds = 120

    def thrift_call(self, method_name, request_argument):
        thrift_request_argument = copy_py_to_thrift(request_argument)
        fn = getattr(cadence.WorkflowService, method_name, None)
        assert fn
        request = fn.request(thrift_request_argument)
        request_payload = cadence.dumps(request)
        call = ThriftFunctionCall.create(TCHANNEL_SERVICE, "WorkflowService::" + method_name, request_payload)
        response = self.connection.call_function(call)
        start_response = cadence.loads(fn.response, response.thrift_payload)
        return start_response

    def start_workflow(self, request: StartWorkflowExecutionRequest) -> Tuple[StartWorkflowExecutionResponse, object]:
        response = self.thrift_call("StartWorkflowExecution", request)
        if not response.success:
            return None, find_error(response)
        return copy_thrift_to_py(response.success), None

    def register_domain(self, request: RegisterDomainRequest) -> [None, object]:
        # RegisterDomain returns void so there is no .success
        response = self.thrift_call("RegisterDomain", request)
        error = find_error(response)
        return None, error

    def poll_for_activity_task(self, request: PollForActivityTaskRequest) -> Tuple[PollForActivityTaskResponse, object]:
        response = self.thrift_call("PollForActivityTask", request)
        if not response.success:
            return None, find_error(response)
        return copy_thrift_to_py(response.success), None

    def respond_activity_task_completed(self, task_token: bytes, result: bytes):
        respond_activity_completed_request = cadence.shared.RespondActivityTaskCompletedRequest()
        respond_activity_completed_request.taskToken = task_token
        respond_activity_completed_request.result = result
        respond_activity_completed_request.identity = self.identity

        respond_activity_completed_response = self.thrift_call("RespondActivityTaskCompleted",
                                                               respond_activity_completed_request)
        error = find_error(respond_activity_completed_request)
        return None, error


