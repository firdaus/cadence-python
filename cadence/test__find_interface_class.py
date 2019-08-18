from unittest import TestCase

from cadence.worker import _find_interface_class
from cadence.workflow import workflow_method


class WorkflowBase:

    @workflow_method()
    def dummy(self):
        pass


class WorkflowImpl(WorkflowBase):

    def dummy(self):
        pass


class TestFindInterfaceClass(TestCase):
    def test_find_interface_class_from_impl(self):
        assert _find_interface_class(WorkflowImpl) == WorkflowBase

    def test_find_interface_class_from_base(self):
        assert _find_interface_class(WorkflowBase) == WorkflowBase



