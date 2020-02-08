import traceback

from cadence.activity_method import activity_method
from cadence.exceptions import ActivityFailureException, WorkflowFailureException
from cadence.workerfactory import WorkerFactory
from cadence.workflow import workflow_method, Workflow, WorkflowClient

TASK_LIST = "TestWorkflowActivityException"
DOMAIN = "sample"


class ComposeGreetingException(Exception):
    pass


# Activities Interface
class GreetingActivities:
    @activity_method(task_list=TASK_LIST, schedule_to_close_timeout_seconds=20)
    def compose_greeting(self, greeting: str, name: str) -> str:
        raise NotImplementedError


# Activities Implementation
class GreetingActivitiesImpl:
    def __init__(self):
        self.invocation_count = 0
        self.details = []

    def compose_greeting(self, greeting: str, name: str):
        raise ComposeGreetingException("Failed to compose greeting") # SOURCE OF EXCEPTION


class TestActivityExceptionWorkflow:
    @workflow_method(task_list=TASK_LIST)
    async def get_greetings(self) -> list:
        raise NotImplementedError


exception_caught: Exception = None


class TestActivityExceptionWorkflowImpl(TestActivityExceptionWorkflow):

    def __init__(self):
        self.greeting_activities: GreetingActivities = Workflow.new_activity_stub(GreetingActivities)

    async def get_greetings(self, name):
        global exception_caught
        try:
            await self.greeting_activities.compose_greeting("Hello", name)  # WORKFLOW METHOD INVOKING ACTIVITY
        except ActivityFailureException as ex:
            exception_caught = ex
            raise ex


def test_workflow_activity_exception():
    factory = WorkerFactory("localhost", 7933, DOMAIN)
    worker = factory.new_worker(TASK_LIST)
    activities_impl = GreetingActivitiesImpl()
    worker.register_activities_implementation(activities_impl, "GreetingActivities")
    worker.register_workflow_implementation_type(TestActivityExceptionWorkflowImpl)
    factory.start()

    client = WorkflowClient.new_client(domain=DOMAIN)
    workflow: TestActivityExceptionWorkflow = client.new_workflow_stub(TestActivityExceptionWorkflow)

    workflow_ex = None
    try:
        workflow.get_greetings("Bob")
    except Exception as ex:
        workflow_ex = ex

    assert isinstance(workflow_ex, WorkflowFailureException)
    assert isinstance(workflow_ex.__cause__, ActivityFailureException)
    assert isinstance(workflow_ex.__cause__.__cause__, ComposeGreetingException)

    assert exception_caught
    assert isinstance(exception_caught, ActivityFailureException)
    assert isinstance(exception_caught.get_cause(), ComposeGreetingException)
    exception_caught.set_cause()
    cause = exception_caught.__cause__
    assert isinstance(cause, ComposeGreetingException)
    assert cause.args == ("Failed to compose greeting",)

    tb = "".join(traceback.format_exception(type(cause), cause, cause.__traceback__))
    assert "SOURCE OF EXCEPTION" in tb

    tb = "".join(traceback.format_exception(type(exception_caught), exception_caught, exception_caught.__traceback__))
    assert "SOURCE OF EXCEPTION" in tb
    assert "WORKFLOW METHOD INVOKING ACTIVITY" in tb

    tb = "".join(traceback.format_exception(type(workflow_ex), workflow_ex, workflow_ex.__traceback__))
    assert "SOURCE OF EXCEPTION" in tb
    assert "WORKFLOW METHOD INVOKING ACTIVITY" in tb

    print("Stopping workers")
    worker.stop()


if __name__ == "__main__":
    test_workflow_activity_exception()

