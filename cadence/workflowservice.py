from __future__ import annotations

from typing import Tuple
from uuid import uuid4

import os
import socket

from cadence.thrift import cadence
from cadence.connection import TChannelConnection, ThriftFunctionCall
from cadence.errors import find_error
from cadence.conversions import copy_thrift_to_py
from cadence.types import PollForActivityTaskResponse

TCHANNEL_SERVICE = "cadence-frontend"


class WorkflowService:

    @classmethod
    def create(cls, host: str, port: int):
        connection = TChannelConnection.open(host, port)
        return cls(connection)

    def __init__(self, connection: TChannelConnection):
        self.connection = connection
        self.execution_start_to_close_timeout_seconds = 86400
        self.task_start_to_close_timeout_seconds = 120
        self.identity = "%d@%s" % (os.getpid(), socket.gethostname())

    def thrift_call(self, method_name, request):
        fn = getattr(cadence.WorkflowService, method_name, None)
        assert fn
        request = fn.request(request)
        request_payload = cadence.dumps(request)
        call = ThriftFunctionCall.create(TCHANNEL_SERVICE, "WorkflowService::" + method_name, request_payload)
        response = self.connection.call_function(call)
        start_response = cadence.loads(fn.response, response.thrift_payload)
        return start_response

    def start_workflow(self, domain, task_list, workflow_type_name, input_value=None, workflow_id=None):
        start_request = cadence.shared.StartWorkflowExecutionRequest()
        start_request.requestId = str(uuid4())
        start_request.domain = domain
        start_request.input = input_value
        start_request.taskList = cadence.shared.TaskList()
        start_request.taskList.name = task_list
        if not workflow_id:
            workflow_id = str(uuid4())
        start_request.workflowId = workflow_id
        start_request.workflowType = cadence.shared.WorkflowType()
        start_request.workflowType.name = workflow_type_name
        start_request.executionStartToCloseTimeoutSeconds = self.execution_start_to_close_timeout_seconds
        start_request.taskStartToCloseTimeoutSeconds = self.task_start_to_close_timeout_seconds

        start_response = self.thrift_call("StartWorkflowExecution", start_request)
        if not start_response.success:
            return None, find_error(start_response)
        return start_response.success.runId, None

    def register_domain(self, name: str, description: str = "", workflow_execution_retention_period_in_days=0):
        register_request = cadence.shared.RegisterDomainRequest()
        register_request.name = name
        register_request.description = description
        register_request.workflowExecutionRetentionPeriodInDays = workflow_execution_retention_period_in_days

        # RegisterDomain returns void so there is no .success
        register_response = self.thrift_call("RegisterDomain", register_request)
        error = find_error(register_response)
        return None, error

    def poll_for_activity_task(self, domain: str, task_list: str) -> Tuple[PollForActivityTaskResponse, object]:
        poll_activity_request = cadence.shared.PollForActivityTaskRequest()
        poll_activity_request.domain = domain
        poll_activity_request.identity = self.identity
        poll_activity_request.taskList = cadence.shared.TaskList()
        poll_activity_request.taskList.name = task_list

        poll_activity_response = self.thrift_call("PollForActivityTask", poll_activity_request)
        if not poll_activity_response.success:
            return None, find_error(poll_activity_response)

        return copy_thrift_to_py(poll_activity_response.success, PollForActivityTaskResponse), None

    def respond_activity_task_completed(self, task_token: bytes, result: bytes):
        respond_activity_completed_request = cadence.shared.RespondActivityTaskCompletedRequest()
        respond_activity_completed_request.taskToken = task_token
        respond_activity_completed_request.result = result
        respond_activity_completed_request.identity = self.identity

        respond_activity_completed_response = self.thrift_call("RespondActivityTaskCompleted",
                                                               respond_activity_completed_request)
        error = find_error(respond_activity_completed_request)
        return None, error


