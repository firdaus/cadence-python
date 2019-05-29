from unittest import TestCase
import logging.config
from uuid import uuid4

from py4j.java_gateway import JavaGateway

from cadence.tests import init_test_logging
from cadence.worker import Worker
from cadence.workflow import workflow_method

init_test_logging()


class GreetingWorkflow:
    @workflow_method(task_list="python-test-tasklist", impl=True)
    async def get_greeting(self, name):
        return f"Hello {name}"


class TestWorkflowExecutionFromJava(TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.task_list = "task-list-" + str(uuid4())
        cls.worker = worker = Worker("localhost", 7933, "test-domain",cls.task_list)
        worker.register_workflow_implementation_type(GreetingWorkflow)
        worker.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.worker.stop()

    def setUp(self) -> None:
        pass

    def test(self):
        gateway = JavaGateway()
        stub = gateway.jvm.GreetingWorkflow.getStub(self.task_list)
        greeting = stub.getGreeting("World")
        self.assertEqual("Hello World", greeting)


