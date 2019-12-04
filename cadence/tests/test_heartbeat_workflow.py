from cadence.activity import Activity
from cadence.cadence_types import WorkflowExecution
from cadence.workerfactory import WorkerFactory
from cadence.activity_method import activity_method, RetryParameters
from cadence.workflow import workflow_method, Workflow, WorkflowClient

TASK_LIST = "TestHeartbeatWorkflow"
DOMAIN = "sample"


# Activities Interface
class GreetingActivities:
    @activity_method(task_list=TASK_LIST, schedule_to_close_timeout_seconds=2)
    def compose_greeting(self, greeting: str, name: str) -> str:
        raise NotImplementedError


# Activities Implementation
class GreetingActivitiesImpl:
    def __init__(self):
        self.invocation_count = 0
        self.details = []

    def compose_greeting(self, greeting: str, name: str):
        self.invocation_count += 1
        self.details.append(Activity.get_heartbeat_details())
        Activity.heartbeat(self.invocation_count)

        if self.invocation_count == 3:
            return greeting + " " + name + "!"
        else:
            raise Exception("Failure")


class TestHeartbeatWorkflow:
    @workflow_method(task_list=TASK_LIST)
    async def get_greetings(self) -> list:
        raise NotImplementedError


class TestHeartbeatWorkflowImpl(TestHeartbeatWorkflow):

    def __init__(self):
        retry_parameters = RetryParameters(initial_interval_in_seconds=1, backoff_coefficient=2.0, maximum_attempts=3)
        self.greeting_activities: GreetingActivities = Workflow.new_activity_stub(GreetingActivities,
                                                                                  retry_parameters=retry_parameters)

    async def get_greetings(self, name):
        return await self.greeting_activities.compose_greeting("Hello", name)


def test_heartbeat_workflow():
    factory = WorkerFactory("localhost", 7933, DOMAIN)
    worker = factory.new_worker(TASK_LIST)
    activities_impl = GreetingActivitiesImpl()
    worker.register_activities_implementation(activities_impl, "GreetingActivities")
    worker.register_workflow_implementation_type(TestHeartbeatWorkflowImpl)
    factory.start()

    client = WorkflowClient.new_client(domain=DOMAIN)
    workflow: TestHeartbeatWorkflow = client.new_workflow_stub(TestHeartbeatWorkflow)

    workflow.get_greetings("Bob")

    assert activities_impl.details == [None, 1, 2]
    assert activities_impl.invocation_count == 3

    print("Stopping workers")
    worker.stop()
