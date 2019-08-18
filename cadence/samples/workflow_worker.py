import logging

from cadence.activity_method import activity_method
from cadence.workerfactory import WorkerFactory
from cadence.workflow import workflow_method, Workflow

logging.basicConfig(level=logging.DEBUG)


# Interface for activity Implemented in Java
class GreetingActivities:
    @activity_method(task_list="HelloActivity", schedule_to_close_timeout_seconds=2)
    def composeGreeting(self, greeting: str, name: str) -> str:
        pass


class GreetingWorkflowImpl:

    def __init__(self):
        self.greeting_activities = Workflow.new_activity_stub(GreetingActivities)

    @workflow_method(name='GreetingWorkflow::getGreeting')
    async def get_greeting(self, name):
        greeting = await self.greeting_activities.composeGreeting("Hello", name)
        return f"Got from Java {greeting}"


if __name__ == '__main__':
    factory = WorkerFactory("localhost", 7933, "sample")
    worker = factory.new_worker("python-tasklist")
    worker.register_workflow_implementation_type(GreetingWorkflowImpl)
    factory.start()
