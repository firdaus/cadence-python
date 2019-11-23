from cadence.activity import Activity
from cadence.cadence_types import WorkflowExecution
from cadence.workerfactory import WorkerFactory
from cadence.activity_method import activity_method
from cadence.workflow import workflow_method, Workflow, WorkflowClient

TASK_LIST = "TestActivityContext"
DOMAIN = "sample"

task_token: bytes = None
workflow_execution: WorkflowExecution = None
domain: str = None

# Activities Interface
class GreetingActivities:
    @activity_method(task_list=TASK_LIST, schedule_to_close_timeout_seconds=2)
    def compose_greeting(self, greeting: str, name: str) -> str:
        raise NotImplementedError


# Activities Implementation
class GreetingActivitiesImpl:
    def compose_greeting(self, greeting: str, name: str):
        global task_token, workflow_execution, domain
        task_token = Activity.get_task_token()
        workflow_execution = Activity.get_workflow_execution()
        domain = Activity.get_domain()
        return greeting + " " + name + "!"


class TestActivityContext:
    @workflow_method(task_list=TASK_LIST)
    async def get_greetings(self) -> list:
        raise NotImplementedError


class TestActivityContextImpl(TestActivityContext):

    def __init__(self):
        self.greeting_activities: GreetingActivities = Workflow.new_activity_stub(GreetingActivities)

    async def get_greetings(self, name):
        return await self.greeting_activities.compose_greeting("Hello", name)


def test_activity_context():
    factory = WorkerFactory("localhost", 7933, DOMAIN)
    worker = factory.new_worker(TASK_LIST)
    worker.register_activities_implementation(GreetingActivitiesImpl(), "GreetingActivities")
    worker.register_workflow_implementation_type(TestActivityContextImpl)
    factory.start()

    client = WorkflowClient.new_client(domain=DOMAIN)
    workflow: TestActivityContext = client.new_workflow_stub(TestActivityContext)

    workflow.get_greetings("Bob")
    global task_token, workflow_execution, domain
    assert task_token is not None
    assert workflow_execution is not None
    assert workflow_execution.workflow_id is not None
    assert workflow_execution.run_id is not None
    assert domain is not None
    assert domain == DOMAIN

    print("Stopping workers")
    worker.stop()
