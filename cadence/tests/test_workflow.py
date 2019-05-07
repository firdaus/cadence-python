import unittest

from cadence.cadence_types import WorkflowIdReusePolicy
from cadence.workflow import workflow_method


class DummyWorkflow:

    @workflow_method
    def method_annotated_plain(self):
        pass

    @workflow_method()
    def method_annotated_decorator_call(self):
        pass

    @workflow_method(name="NAME",
                     workflow_id="WORKFLOW_ID",
                     workflow_id_reuse_policy=WorkflowIdReusePolicy.AllowDuplicate,
                     execution_start_to_close_timeout_seconds=99999,
                     task_start_to_close_timeout_seconds=123456,
                     task_list="TASK_LIST")
    def method_with_decorator_call_arguments(self):
        pass


class TestWorkflowMethod(unittest.TestCase):

    def setUp(self) -> None:
        pass

    def test_method_annotated_plain(self):
        fn = DummyWorkflow.method_annotated_plain
        attributes = dir(fn)
        self.assertIn("_name", attributes)
        self.assertEqual("DummyWorkflow::method_annotated_plain", fn._name)
        self.assertIn("_workflow_id", attributes)
        self.assertIn("_workflow_id_reuse_policy", attributes)
        self.assertIn("_execution_start_to_close_timeout_seconds", attributes)
        self.assertIn("_task_start_to_close_timeout_seconds", attributes)
        self.assertIn("_task_list", attributes)

    def test_method_annotated_decorator_call(self):
        fn = DummyWorkflow.method_annotated_decorator_call
        attributes = dir(fn)
        self.assertIn("_name", attributes)
        self.assertEqual("DummyWorkflow::method_annotated_decorator_call", fn._name)
        self.assertIn("_workflow_id", attributes)
        self.assertIn("_workflow_id_reuse_policy", attributes)
        self.assertIn("_execution_start_to_close_timeout_seconds", attributes)
        self.assertIn("_task_start_to_close_timeout_seconds", attributes)
        self.assertIn("_task_list", attributes)

    def test_method_with_decorator_call_arguments(self):
        fn = DummyWorkflow.method_with_decorator_call_arguments
        self.assertEqual("NAME", fn._name)
        self.assertEqual("WORKFLOW_ID", fn._workflow_id)
        self.assertEqual(WorkflowIdReusePolicy.AllowDuplicate, fn._workflow_id_reuse_policy)
        self.assertEqual(99999, fn._execution_start_to_close_timeout_seconds)
        self.assertEqual(123456, fn._task_start_to_close_timeout_seconds)
        self.assertEqual("TASK_LIST", fn._task_list)


