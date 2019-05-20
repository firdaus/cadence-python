from unittest import TestCase
from unittest.mock import Mock

from cadence.decision_loop import DecisionContext


class DecisionContextDestroyTest(TestCase):

    def setUp(self) -> None:
        self.workflow_task = Mock()
        self.decision_context = DecisionContext(execution_id="", workflow_type=Mock(), worker=Mock())
        self.decision_context.workflow_task = self.workflow_task

    def test_destroy(self):
        self.decision_context.destroy()
        self.workflow_task.destroy.assert_called()
