from unittest import TestCase
from unittest.mock import Mock

from cadence.decision_loop import WorkflowTask, Status


class WorkflowTaskDestroyTest(TestCase):

    def setUp(self) -> None:
        self.workflow_task = WorkflowTask(task_id="", workflow_input=[], worker=Mock(), workflow_type=Mock(),
                                          decision_context=Mock())
        self.task = Mock()
        self.workflow_task.task = self.task
        self.workflow_task.status = Status.RUNNING

    def test_destroy(self):
        self.workflow_task.destroy()
        self.task.cancel.assert_called()
        self.assertEqual(Status.DONE, self.workflow_task.status)
