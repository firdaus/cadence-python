from unittest import TestCase
from unittest.mock import Mock

from cadence.decision_loop import WorkflowMethodTask, Status


class WorkflowMethodTaskDestroyTest(TestCase):

    def setUp(self) -> None:
        self.workflow_task = WorkflowMethodTask(task_id="", workflow_input=[], worker=Mock(), workflow_type=Mock(),
                                                decider=Mock())
        self.task = Mock()
        self.workflow_task.task = self.task
        self.workflow_task.status = Status.RUNNING

    def test_destroy(self):
        self.workflow_task.destroy()
        self.task.cancel.assert_called()
        self.assertEqual(Status.DONE, self.workflow_task.status)
