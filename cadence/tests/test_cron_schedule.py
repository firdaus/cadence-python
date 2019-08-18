from unittest import TestCase
from unittest.mock import MagicMock

from cadence.cadence_types import StartWorkflowExecutionRequest
from cadence.workflow import cron_schedule, workflow_method, create_start_workflow_request


@workflow_method(execution_start_to_close_timeout_seconds=10, task_list="dummy")
@cron_schedule("*/2 * * * *")
def cron_first():
    pass


@cron_schedule("*/2 * * * *")
@workflow_method(execution_start_to_close_timeout_seconds=10, task_list="dummy")
def cron_last():
    pass


class CronScheduleTest(TestCase):

    def test_cron_first(self):
        self.assertEqual("*/2 * * * *", cron_first._workflow_method._cron_schedule)

    def test_cron_last(self):
        self.assertEqual("*/2 * * * *", cron_last._workflow_method._cron_schedule)


class CreateStartWorkflowRequestTest(TestCase):

    def test_cron_first(self):
        workflow_client = MagicMock()
        request: StartWorkflowExecutionRequest = create_start_workflow_request(workflow_client, cron_first._workflow_method, [])
        self.assertEqual("*/2 * * * *", request.cron_schedule)

    def test_cron_last(self):
        workflow_client = MagicMock()
        request: StartWorkflowExecutionRequest = create_start_workflow_request(workflow_client, cron_last._workflow_method, [])
        self.assertEqual("*/2 * * * *", request.cron_schedule)
