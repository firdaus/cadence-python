import time

import pytest

from cadence.exceptions import QueryFailureException
from cadence.workerfactory import WorkerFactory
from cadence.workflow import workflow_method, signal_method, Workflow, WorkflowClient, query_method

TASK_LIST = "TestQueryWorkflow"
DOMAIN = "sample"


class GreetingException(Exception):
    pass


class TestQueryWorkflow:

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


class TestQueryWorkflowImpl(TestQueryWorkflow):

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


def test_query_workflow():
    factory = WorkerFactory("localhost", 7933, DOMAIN)
    worker = factory.new_worker(TASK_LIST)
    worker.register_workflow_implementation_type(TestQueryWorkflowImpl)
    factory.start()

    client = WorkflowClient.new_client(domain=DOMAIN)
    workflow: TestQueryWorkflow = client.new_workflow_stub(TestQueryWorkflow)
    workflow_ec = WorkflowClient.start(workflow.get_greetings)

    assert workflow.get_message() == "initial-message"
    workflow.put_message("second-message")
    assert workflow.get_message() == "second-message"

    with pytest.raises(QueryFailureException) as exc_info:
        workflow.get_message_fail()
    ex = exc_info.value
    assert isinstance(ex.__cause__, GreetingException)

    workflow.put_message("done")

    client.wait_for_close(workflow_ec)

    assert workflow.get_message() == "done"

    print("Stopping workers")
    worker.stop()
