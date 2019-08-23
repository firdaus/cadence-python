from time import sleep
from unittest import TestSuite

from cadence.workerfactory import WorkerFactory
from cadence.workflow import workflow_method, signal_method, Workflow, WorkflowClient

TASK_LIST = "TestSignal"
DOMAIN = "sample"


class TestSignalWorkflow:
    @workflow_method(task_list=TASK_LIST)
    async def get_greetings(self) -> list:
        raise NotImplementedError

    @signal_method
    async def wait_for_name(self, name: str):
        raise NotImplementedError

    @signal_method
    async def exit(self):
        raise NotImplementedError


class TestSignalWorkflowImpl(TestSignalWorkflow):

    def __init__(self):
        self.message_queue = []
        self.exit = False

    async def get_greetings(self) -> list:
        received_messages = []
        while True:
            await Workflow.await_till(lambda: self.message_queue or self.exit)
            if not self.message_queue or self.exit:
                return received_messages
            message = self.message_queue.pop()
            received_messages.append(message)

    async def wait_for_name(self, name: str):
        self.message_queue.append("Hello " + name + "!")

    async def exit(self):
        self.exit = True


def test_signal_workflow():
    factory = WorkerFactory("localhost", 7933, DOMAIN)
    worker = factory.new_worker(TASK_LIST)
    worker.register_workflow_implementation_type(TestSignalWorkflowImpl)
    factory.start()

    client = WorkflowClient.new_client(domain=DOMAIN)
    workflow: TestSignalWorkflow = client.new_workflow_stub(TestSignalWorkflow)
    execution = WorkflowClient.start(workflow.get_greetings)

    workflow.wait_for_name("Bob")
    # Sleep for a while so that it processes the signal first
    sleep(5)
    workflow.exit()

    result = client.wait_for_close(execution)
    worker.stop()
    assert result == ["Hello Bob!"]
