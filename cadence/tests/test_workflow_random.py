import pytest

from cadence.workerfactory import WorkerFactory
from cadence.workflow import workflow_method, Workflow, WorkflowClient

TASK_LIST = "TestWorkflowRandom"
DOMAIN = "sample"

checkpoint_values = {}


def record_value(key, v):
    values = checkpoint_values.setdefault(key, [])
    values.append(v)


class TestRandomWorkflow:
    @workflow_method(task_list=TASK_LIST)
    async def get_greetings(self) -> list:
        raise NotImplementedError


class TestRandomWorkflowImpl(TestRandomWorkflow):

    def __init__(self):
        pass

    async def get_greetings(self) -> None:
        record_value("uuid-checkpoint-1", Workflow.random_uuid())
        Workflow.sleep(1)
        record_value("uuid-checkpoint-2", Workflow.random_uuid())
        Workflow.sleep(1)
        record_value("uuid-checkpoint-3", Workflow.random_uuid())
        Workflow.sleep(1)

        random = Workflow.new_random()
        record_value("random-checkpoint-1", random.randint(0, 2 ** 64))
        record_value("random-checkpoint-2", random.randint(0, 2 ** 64))
        Workflow.sleep(1)

        random = Workflow.new_random()
        record_value("random-checkpoint-3", random.randint(0, 2 ** 64))
        record_value("random-checkpoint-4", random.randint(0, 2 ** 64))
        Workflow.sleep(1)

        random = Workflow.new_random()
        record_value("random-checkpoint-5", random.randint(0, 2 ** 64))
        record_value("random-checkpoint-6", random.randint(0, 2 ** 64))
        Workflow.sleep(1)


@pytest.mark.repeat(3)
def test_workflow_random():
    checkpoint_values.clear()
    factory = WorkerFactory("localhost", 7933, DOMAIN)
    worker = factory.new_worker(TASK_LIST)
    worker.register_workflow_implementation_type(TestRandomWorkflowImpl)
    factory.start()

    client = WorkflowClient.new_client(domain=DOMAIN)
    workflow: TestRandomWorkflow = client.new_workflow_stub(TestRandomWorkflow)
    workflow.get_greetings()

    # Verify that the value is always the same at each checkpoint
    for checkpoint, values in checkpoint_values.items():
        assert all(v == values[0] for v in values)

    # Verify that each checkpoint produced a unique value
    values = [v[0] for k, v in checkpoint_values.items()]
    assert len(set(values)) == 9

    print("Stopping workers")
    worker.stop()
