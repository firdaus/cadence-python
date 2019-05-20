from unittest import TestCase
from unittest.mock import Mock

from cadence.decision_loop import ReplayDecider


class ReplayDeciderDestroyTest(TestCase):

    def setUp(self) -> None:
        self.workflow_task = Mock()
        self.decider = ReplayDecider(execution_id="", workflow_type=Mock(), worker=Mock())
        self.decider.workflow_task = self.workflow_task

    def test_destroy(self):
        self.decider.destroy()
        self.workflow_task.destroy.assert_called()
