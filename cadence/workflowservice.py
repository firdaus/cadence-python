from __future__ import annotations
from uuid import uuid4

import thriftrw
import os
import socket

from cadence.connection import TChannelConnection, ThriftFunctionCall
from cadence.errors import find_error

this_dir = os.path.dirname(__file__)
cadence_thrift = os.path.join(this_dir, "thrift/cadence.thrift")
cadence = thriftrw.load(cadence_thrift)

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
        start_request.taskList.kind = cadence.shared.TaskListKind.NORMAL
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
