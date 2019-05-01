from unittest import TestCase

from cadence.conversions import camel_to_snake, copy_thrift_to_py
from cadence.types import PollForActivityTaskResponse
from cadence.thrift import cadence


class TestCamelToSnake(TestCase):

    def test(self):
        self.assertEqual("schedule_to_close_timeout_seconds",
                         camel_to_snake("scheduleToCloseTimeoutSeconds"))


class TestCopyThriftToPy(TestCase):

    def setUp(self) -> None:
        self.thrift_object = cadence.shared.PollForActivityTaskResponse()
        self.thrift_object.taskToken = "TASK_TOKEN"
        self.thrift_object.workflowExecution = cadence.shared.WorkflowExecution()
        self.thrift_object.workflowExecution.workflowId = "WORKFLOW_ID"
        self.thrift_object.workflowExecution.runId = "RUN_ID"

    def test_copy(self):
        obj: PollForActivityTaskResponse = copy_thrift_to_py(self.thrift_object, PollForActivityTaskResponse)
        assert isinstance(obj, PollForActivityTaskResponse)
        self.assertEqual("TASK_TOKEN", obj.task_token)
        self.assertEqual("WORKFLOW_ID", obj.workflow_execution.workflow_id)
        self.assertEqual("RUN_ID", obj.workflow_execution.run_id)
