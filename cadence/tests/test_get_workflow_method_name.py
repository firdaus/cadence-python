from unittest import TestCase

from cadence.workflow import get_workflow_method_name

class DummyWorkflowTest:
    def dummy(self):
        pass

class Test_get_workflow_method_name(TestCase):
    def test_toplevel_class(self):
        self.assertEqual("DummyWorkflowTest::dummy", get_workflow_method_name(DummyWorkflowTest.dummy))

    def test_inner_class_get_workflow_method_name(self):
        class DummyWorkflow:
            def dummy(self):
                pass

        self.assertEqual("DummyWorkflow::dummy", get_workflow_method_name(DummyWorkflow.dummy))

