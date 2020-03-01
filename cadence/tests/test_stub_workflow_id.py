import time

import pytest

from cadence.exceptions import QueryFailureException
from cadence.workerfactory import WorkerFactory
from cadence.workflow import workflow_method, signal_method, Workflow, WorkflowClient, query_method

TASK_LIST = "TestStubWorkflowId"
DOMAIN = "sample"


class GreetingException(Exception):
    pass


class TestStubWorkflowId:

    @query_method()
    async def get_message(self) -> str:
        raise NotImplementedError

    @query_method()
    async def get_message_fail(self) -> str:
        raise NotImplementedError

    @signal_method()
    async def put_message(self, message):
        raise NotImplementedError

    @workflow_method(task_list=TASK_LIST)
    async def get_greetings(self) -> list:
        raise NotImplementedError


class TestStubWorkflowIdImpl(TestStubWorkflowId):

    def __init__(self):
        self.message = ""

    async def get_message(self) -> str:
        return self.message

    async def get_message_fail(self) -> str:
        raise GreetingException("error from query")

    async def put_message(self, message):
        self.message = message

    async def get_greetings(self) -> list:
        self.message = "initial-message"
        await Workflow.await_till(lambda: self.message == "done")
        return "finished"


def test_stub_workflow_id():
    factory = WorkerFactory("localhost", 7933, DOMAIN)
    worker = factory.new_worker(TASK_LIST)
    worker.register_workflow_implementation_type(TestStubWorkflowIdImpl)
    factory.start()

    client = WorkflowClient.new_client(domain=DOMAIN)
    workflow: TestStubWorkflowId = client.new_workflow_stub(TestStubWorkflowId)
    context = WorkflowClient.start(workflow.get_greetings)

    stub: TestStubWorkflowId = client.new_workflow_stub_from_workflow_id(TestStubWorkflowId,
                                                                         workflow_id=context.workflow_execution.workflow_id)
    stub.put_message("abc")
    assert stub.get_message() == "abc"

    stub.put_message("done")
    assert client.wait_for_close_with_workflow_id(context.workflow_execution.workflow_id) == "finished"

    print("Stopping workers")
    worker.stop()
