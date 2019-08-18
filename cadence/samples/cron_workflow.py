import logging
import sys
from time import sleep

from cadence.workerfactory import WorkerFactory
from cadence.workflow import workflow_method, WorkflowClient, cron_schedule

logging.basicConfig(level=logging.DEBUG)

TASK_LIST = "periodically-executed-workflow-task-list"
DOMAIN = "sample"


# Workflow Interface
class PeriodicallyExecutedWorkflow:
    @workflow_method(workflow_id="periodically_executed_workflow_method",
                     execution_start_to_close_timeout_seconds=10, task_list=TASK_LIST)
    @cron_schedule("*/5 * * * *")
    async def periodically_executed_workflow_method(self, value):
        raise NotImplementedError


# Workflow Implementation
class PeriodicallyExecutedWorkflowImpl(PeriodicallyExecutedWorkflow):

    def __init__(self):
        pass

    async def periodically_executed_workflow_method(self, value):
        print("periodically_executed_workflow_method executed with args:" + value)
        return None


if __name__ == '__main__':
    factory = WorkerFactory("localhost", 7933, DOMAIN)
    worker = factory.new_worker(TASK_LIST)
    worker.register_workflow_implementation_type(PeriodicallyExecutedWorkflowImpl)
    factory.start()

    client = WorkflowClient.new_client(domain=DOMAIN)
    workflow: PeriodicallyExecutedWorkflow = client.new_workflow_stub(PeriodicallyExecutedWorkflow)
    execution = WorkflowClient.start(workflow.periodically_executed_workflow_method, "blah blah")
    print("Started: workflow_id={} run_id={}".format(execution.workflow_id, execution.run_id))

    sleep(60 * 20)

    print("Stopping workers....")
    worker.stop()
    print("Workers stopped...")
    sys.exit(0)
