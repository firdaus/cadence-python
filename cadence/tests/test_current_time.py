from cadence.workerfactory import WorkerFactory
from cadence.workflow import workflow_method, Workflow, WorkflowClient

TASK_LIST = "TestWorkflowNow"
DOMAIN = "sample"


class TestCurrentTime:
    @workflow_method(task_list=TASK_LIST)
    async def get_greetings(self) -> list:
        raise NotImplementedError


timestamps = {}


def record_timestamp(key, ts):
    timestamp = timestamps.setdefault(key, [])
    timestamp.append(ts)


class TestCurrentTimeImpl(TestCurrentTime):

    def __init__(self):
        pass

    async def get_greetings(self):
        record_timestamp("checkpoint-1", Workflow.now())
        await Workflow.sleep(20)
        record_timestamp("checkpoint-2", Workflow.now())
        await Workflow.sleep(30)
        record_timestamp("checkpoint-3", Workflow.now())


def test_current_time():
    factory = WorkerFactory("localhost", 7933, DOMAIN)
    worker = factory.new_worker(TASK_LIST)
    worker.register_workflow_implementation_type(TestCurrentTimeImpl)
    factory.start()

    client = WorkflowClient.new_client(domain=DOMAIN)
    workflow: TestCurrentTime = client.new_workflow_stub(TestCurrentTime)

    workflow.get_greetings()

    assert len(timestamps["checkpoint-1"]) >= 3
    assert len(timestamps["checkpoint-2"]) >= 2
    assert len(timestamps["checkpoint-3"]) >= 1

    for checkpoint, values in timestamps.items():
        assert all(v == values[0] for v in values)

    assert (timestamps["checkpoint-2"][0] - timestamps["checkpoint-1"][0]).total_seconds() > 20
    assert (timestamps["checkpoint-3"][0] - timestamps["checkpoint-2"][0]).total_seconds() > 30

    print("Stopping workers")
    worker.stop()
