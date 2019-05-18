import logging

from cadence.workerfactory import WorkerFactory
from cadence.workflow import workflow_method

logging.basicConfig(level=logging.DEBUG)


class GreetingWorkflowImpl:

    @workflow_method(name='GreetingWorkflow::getGreeting')
    async def get_greeting(self, name):
        return f"Hello, return value from Python {name}"


if __name__ == '__main__':
    factory = WorkerFactory("localhost", 7933, "sample")
    worker = factory.new_worker("python-tasklist")
    worker.register_workflow_implementation_type(GreetingWorkflowImpl)
    factory.start()
