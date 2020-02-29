import logging

from cadence.tests.interceptor_testing_utils import reset_counter_filter_counter, LOGGING, get_counter_filter_counter
from cadence.workerfactory import WorkerFactory
from cadence.workflow import workflow_method, Workflow, WorkflowClient

TASK_LIST = "TestWorkflowLogger"
DOMAIN = "sample"


class TestWorkflowLogger:
    @workflow_method(task_list=TASK_LIST)
    async def get_greetings(self) -> list:
        raise NotImplementedError


class TestWorkflowLoggerImpl(TestWorkflowLogger):

    def __init__(self):
        pass

    async def get_greetings(self):
        logger = Workflow.get_logger("test-logger")
        logger.info("********Test %d", 1)
        await Workflow.sleep(10)
        logger.info("********Test %d", 2)
        await Workflow.sleep(10)
        logger.info("********Test %d", 3)
        await Workflow.sleep(10)
        logger.info("********Test %d", 4)
        await Workflow.sleep(10)
        logger.info("********Test %d", 5)


def test_workflow_logger():
    reset_counter_filter_counter()
    logging.config.dictConfig(LOGGING)

    factory = WorkerFactory("localhost", 7933, DOMAIN)
    worker = factory.new_worker(TASK_LIST)
    worker.register_workflow_implementation_type(TestWorkflowLoggerImpl)
    factory.start()

    client = WorkflowClient.new_client(domain=DOMAIN)
    workflow: TestWorkflowLogger = client.new_workflow_stub(TestWorkflowLogger)

    workflow.get_greetings()
    assert get_counter_filter_counter() == 5

    print("Stopping workers")
    worker.stop()
