import traceback

from cadence.workerfactory import WorkerFactory
from cadence.activity_method import activity_method, RetryParameters
from cadence.workflow import workflow_method, Workflow, WorkflowClient

TASK_LIST = "TestWorkflowException"
DOMAIN = "sample"


class GreetingException(Exception):
    pass


class TestWorkflowExceptionWorkflow:
    @workflow_method(task_list=TASK_LIST)
    async def get_greetings(self) -> list:
        raise NotImplementedError


class TestWorkflowExceptionWorkflowImpl(TestWorkflowExceptionWorkflow):

    def __init__(self):
        pass

    async def get_greetings(self, name):
        raise GreetingException("Could not create greeting") # Impl method (Don't remove this comment)


def test_workflow_workflow_exception():
    factory = WorkerFactory("localhost", 7933, DOMAIN)
    worker = factory.new_worker(TASK_LIST)
    worker.register_workflow_implementation_type(TestWorkflowExceptionWorkflowImpl)
    factory.start()

    client = WorkflowClient.new_client(domain=DOMAIN)
    workflow: TestWorkflowExceptionWorkflow = client.new_workflow_stub(TestWorkflowExceptionWorkflow)

    exception_caught = False
    exception = None
    try:
        workflow.get_greetings("Bob")
    except GreetingException as ex:
        exception_caught = True
        exception = ex

    assert exception_caught
    assert isinstance(exception, GreetingException)
    assert exception.__traceback__
    tb = "".join(traceback.format_exception(type(GreetingException), exception, exception.__traceback__))
    assert "get_greetings" in tb
    assert "Impl method" in tb

    print("Stopping workers")
    worker.stop()
