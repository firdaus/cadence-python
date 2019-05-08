import logging

from cadence.workerfactory import WorkerFactory
from cadence.workflow import workflow_method, Workflow

logging.basicConfig(level=logging.DEBUG)


class GreetingWorkflowImpl:

    def __init__(self, workflow: Workflow):
        self.workflow = workflow

    @workflow_method(name='GreetingWorkflow::getGreeting')
    def get_greeting(self, name):
        return f"Hello, return value from Python {name}"


if __name__ == '__main__':
    factory = WorkerFactory("localhost", 7933, "sample")
    worker = factory.new_worker("python-tasklist")
    worker.register_workflow_implementation_type(GreetingWorkflowImpl)
    factory.start()
