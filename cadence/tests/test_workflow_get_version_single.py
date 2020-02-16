import sys
from time import sleep

from cadence.clock_decision_context import DEFAULT_VERSION
from cadence.workerfactory import WorkerFactory
from cadence.workflow import workflow_method, Workflow, WorkflowClient

TASK_LIST = "TestWorkflowGetVersionSingle"
DOMAIN = "sample"

version_found_in_step_1 = None
version_found_in_step_2 = None


class TestWorkflowGetVersionSingle:
    @workflow_method(task_list=TASK_LIST)
    async def get_greetings(self) -> list:
        raise NotImplementedError


class TestWorkflowGetVersionSingleImpl(TestWorkflowGetVersionSingle):

    def __init__(self):
        pass

    async def get_greetings(self):
        global version_found_in_step_1, version_found_in_step_2
        version_found_in_step_1 = Workflow.get_version("first-item", DEFAULT_VERSION, 2)
        await Workflow.sleep(60)
        version_found_in_step_2 = Workflow.get_version("first-item", DEFAULT_VERSION, 2)


def test_workflow_workflow_get_version_single():
    factory = WorkerFactory("localhost", 7933, DOMAIN)
    worker = factory.new_worker(TASK_LIST)
    worker.register_workflow_implementation_type(TestWorkflowGetVersionSingleImpl)
    factory.start()

    client = WorkflowClient.new_client(domain=DOMAIN)
    workflow: TestWorkflowGetVersionSingle = client.new_workflow_stub(TestWorkflowGetVersionSingle)
    workflow.get_greetings()

    assert version_found_in_step_1 == 2
    assert version_found_in_step_2 == 2

    print("Stopping workers")
    worker.stop(background=True)
