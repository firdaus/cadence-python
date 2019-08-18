from unittest import TestCase

from cadence.worker import _get_wm
from cadence.workflow import workflow_method


class WorkflowBase:

    @workflow_method(workflow_id="blah-blah")
    def dummy(self):
        pass


class WorkflowImpl(WorkflowBase):

    def dummy(self):
        pass


class TestGetWM(TestCase):

    def test_get_wm(self):
        wm = _get_wm(WorkflowImpl, "dummy")
        assert wm._workflow_id == "blah-blah"
