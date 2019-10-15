import time

from cadence.workerfactory import WorkerFactory
from cadence.workflow import workflow_method, signal_method, Workflow, WorkflowClient

TASK_LIST = "TestAwaitTimeout"
DOMAIN = "sample"


class TestAwaitTimeoutWorkflow:
    @workflow_method(task_list=TASK_LIST)
    async def get_greetings(self) -> bool:
        raise NotImplementedError

    @workflow_method(task_list=TASK_LIST)
    async def get_greetings_no_timeout(self) -> bool:
        raise NotImplementedError

    @signal_method
    async def wait_for_name(self, name: str):
        raise NotImplementedError


class TestAwaitTimeoutWorkflowImpl(TestAwaitTimeoutWorkflow):

    def __init__(self):
        self.message_queue = []

    async def get_greetings(self) -> bool:
        # Returns False if timed out
        unblocked = await Workflow.await_till(lambda: self.message_queue, 60)
        return unblocked

    async def get_greetings_no_timeout(self) -> bool:
        unblocked = await Workflow.await_till(lambda: self.message_queue)
        return unblocked

    async def wait_for_name(self, name: str):
        self.message_queue.append("Hello " + name + "!")


def test_await_timeout():
    factory = WorkerFactory("localhost", 7933, DOMAIN)
    worker = factory.new_worker(TASK_LIST)
    worker.register_workflow_implementation_type(TestAwaitTimeoutWorkflowImpl)
    factory.start()

    client = WorkflowClient.new_client(domain=DOMAIN)
    workflow: TestAwaitTimeoutWorkflow = client.new_workflow_stub(TestAwaitTimeoutWorkflow)

    start_time = time.time()
    assert workflow.get_greetings() is False
    end_time = time.time()

    assert end_time - start_time > 60

    print("Stopping workers")
    worker.stop()


def test_await_condition_met():
    factory = WorkerFactory("localhost", 7933, DOMAIN)
    worker = factory.new_worker(TASK_LIST)
    worker.register_workflow_implementation_type(TestAwaitTimeoutWorkflowImpl)
    factory.start()

    client = WorkflowClient.new_client(domain=DOMAIN)
    workflow: TestAwaitTimeoutWorkflow = client.new_workflow_stub(TestAwaitTimeoutWorkflow)

    execution = WorkflowClient.start(workflow.get_greetings)
    time.sleep(10)

    workflow.wait_for_name("Bob")

    result = client.wait_for_close(execution)
    assert result is True

    print("Stopping workers")
    worker.stop()


def test_await_condition_no_timeout():
    factory = WorkerFactory("localhost", 7933, DOMAIN)
    worker = factory.new_worker(TASK_LIST)
    worker.register_workflow_implementation_type(TestAwaitTimeoutWorkflowImpl)
    factory.start()

    client = WorkflowClient.new_client(domain=DOMAIN)
    workflow: TestAwaitTimeoutWorkflow = client.new_workflow_stub(TestAwaitTimeoutWorkflow)

    execution = WorkflowClient.start(workflow.get_greetings_no_timeout)
    time.sleep(10)

    workflow.wait_for_name("Bob")

    result = client.wait_for_close(execution)
    assert result is True

    print("Stopping workers")
    worker.stop()


