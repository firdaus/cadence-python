import time

from cadence.workerfactory import WorkerFactory
from cadence.workflow import workflow_method, signal_method, Workflow, WorkflowClient

TASK_LIST = "TestSleep"
DOMAIN = "sample"


class TestSleepWorkflow:
    @workflow_method(task_list=TASK_LIST)
    async def get_greetings(self) -> list:
        raise NotImplementedError


class TestSleepWorkflowImpl(TestSleepWorkflow):

    def __init__(self):
        pass

    async def get_greetings(self) -> list:
        await Workflow.sleep(20)
        await Workflow.sleep(30)


def test_sleep_workflow():
    factory = WorkerFactory("localhost", 7933, DOMAIN)
    worker = factory.new_worker(TASK_LIST)
    worker.register_workflow_implementation_type(TestSleepWorkflowImpl)
    factory.start()

    client = WorkflowClient.new_client(domain=DOMAIN)
    workflow: TestSleepWorkflow = client.new_workflow_stub(TestSleepWorkflow)

    start_time = time.time()
    workflow.get_greetings()
    end_time = time.time()

    assert end_time - start_time > 50

    print("Stopping workers")
    worker.stop()
