import threading
from time import sleep

from cadence.activity import Activity
from cadence.workerfactory import WorkerFactory
from cadence.activity_method import activity_method, RetryParameters
from cadence.workflow import workflow_method, Workflow, WorkflowClient

TASK_LIST = "TestAsyncActivityCompletion"
DOMAIN = "sample"


# Activities Interface
class GreetingActivities:
    @activity_method(task_list=TASK_LIST, schedule_to_close_timeout_seconds=120)
    def compose_greeting(self, greeting: str, name: str) -> str:
        raise NotImplementedError


def greeting_activities_thread_func(greeting, name, task_token):
    client = WorkflowClient.new_client(domain=DOMAIN)
    activity_completion_client = client.new_activity_completion_client()
    sleep(20)
    return_value = "From thread: " + greeting + " " + name + "!"
    activity_completion_client.complete(task_token, return_value)


# Activities Implementation
class GreetingActivitiesImpl:
    def __init__(self):
        self.invocation_count = 0
        self.details = []

    def compose_greeting(self, greeting: str, name: str):
        Activity.do_not_complete_on_return()
        thread = threading.Thread(target=greeting_activities_thread_func, args=(greeting, name,
                                                                                Activity.get_task_token()))
        thread.start()


class TestAsyncActivityCompletion:
    @workflow_method(task_list=TASK_LIST)
    async def get_greetings(self) -> list:
        raise NotImplementedError


class TestAsyncActivityCompletionImpl(TestAsyncActivityCompletion):

    def __init__(self):
        retry_parameters = RetryParameters(initial_interval_in_seconds=1, backoff_coefficient=2.0, maximum_attempts=3)
        self.greeting_activities: GreetingActivities = Workflow.new_activity_stub(GreetingActivities,
                                                                                  retry_parameters=retry_parameters)


    async def get_greetings(self, name):
        return await self.greeting_activities.compose_greeting("Hello", name)


def test_async_activity_completion_workflow():
    factory = WorkerFactory("localhost", 7933, DOMAIN)
    worker = factory.new_worker(TASK_LIST)
    activities_impl = GreetingActivitiesImpl()
    worker.register_activities_implementation(activities_impl, "GreetingActivities")
    worker.register_workflow_implementation_type(TestAsyncActivityCompletionImpl)
    factory.start()

    client = WorkflowClient.new_client(domain=DOMAIN)
    workflow: TestAsyncActivityCompletion = client.new_workflow_stub(TestAsyncActivityCompletion)

    result = workflow.get_greetings("Bob")

    assert result == "From thread: Hello Bob!"

    print("Stopping workers")
    worker.stop()
