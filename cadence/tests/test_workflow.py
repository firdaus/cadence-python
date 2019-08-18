import unittest
from unittest import TestCase
from unittest.mock import Mock

from cadence.cadence_types import WorkflowIdReusePolicy
from cadence.decision_loop import WorkflowTask, current_workflow_task
from cadence.worker import Worker
from cadence.workerfactory import WorkerFactory
from cadence.workflow import workflow_method, Workflow


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


class DummyWorkflowImpl(DummyWorkflow):
    def method_annotated_plain(self):
        pass

    def method_annotated_decorator_call(self):
        pass

    def method_with_decorator_call_arguments(self):
        pass


class TestWorkflowMethod(unittest.TestCase):

    def setUp(self) -> None:
        pass

    def test_method_annotated_plain(self):
        fn = DummyWorkflow.method_annotated_plain
        assert fn._workflow_method
        attributes = dir(fn._workflow_method)
        self.assertIn("_name", attributes)
        self.assertEqual("DummyWorkflow::method_annotated_plain", fn._workflow_method._name)
        self.assertIn("_workflow_id", attributes)
        self.assertIn("_workflow_id_reuse_policy", attributes)
        self.assertIn("_execution_start_to_close_timeout_seconds", attributes)
        self.assertIn("_task_start_to_close_timeout_seconds", attributes)
        self.assertIn("_task_list", attributes)

    def test_method_annotated_decorator_call(self):
        fn = DummyWorkflow.method_annotated_decorator_call
        attributes = dir(fn._workflow_method)
        self.assertIn("_name", attributes)
        self.assertEqual("DummyWorkflow::method_annotated_decorator_call", fn._workflow_method._name)
        self.assertIn("_workflow_id", attributes)
        self.assertIn("_workflow_id_reuse_policy", attributes)
        self.assertIn("_execution_start_to_close_timeout_seconds", attributes)
        self.assertIn("_task_start_to_close_timeout_seconds", attributes)
        self.assertIn("_task_list", attributes)

    def test_method_with_decorator_call_arguments(self):
        fn = DummyWorkflow.method_with_decorator_call_arguments
        self.assertEqual("NAME", fn._workflow_method._name)
        self.assertEqual("WORKFLOW_ID", fn._workflow_method._workflow_id)
        self.assertEqual(WorkflowIdReusePolicy.AllowDuplicate, fn._workflow_method._workflow_id_reuse_policy)
        self.assertEqual(99999, fn._workflow_method._execution_start_to_close_timeout_seconds)
        self.assertEqual(123456, fn._workflow_method._task_start_to_close_timeout_seconds)
        self.assertEqual("TASK_LIST", fn._workflow_method._task_list)


class TestRegisterWorkflowMethod(unittest.TestCase):

    def setUp(self) -> None:
        pass

    def test_register_workflow_implementation_type(self):
        factory = WorkerFactory("localhost", 7933, "sample")
        worker: Worker = factory.new_worker("python-tasklist")
        worker.register_workflow_implementation_type(DummyWorkflowImpl)
        self.assertIn("DummyWorkflow::method_annotated_plain", worker.workflow_methods)
        self.assertIn("DummyWorkflow::methodAnnotatedPlain", worker.workflow_methods)
        self.assertIn("DummyWorkflow::method_annotated_decorator_call", worker.workflow_methods)
        self.assertIn("DummyWorkflow::methodAnnotatedDecoratorCall", worker.workflow_methods)
        self.assertIn("NAME", worker.workflow_methods)

        (cls, fn) = worker.workflow_methods.get("DummyWorkflow::method_annotated_plain")
        self.assertEqual(DummyWorkflowImpl, cls)
        self.assertEqual(fn, DummyWorkflowImpl.method_annotated_plain)

    def test_register_workflow_implementation_type_no_interface(self):
        factory = WorkerFactory("localhost", 7933, "sample")
        worker: Worker = factory.new_worker("python-tasklist")
        worker.register_workflow_implementation_type(DummyWorkflow)
        self.assertIn("DummyWorkflow::method_annotated_plain", worker.workflow_methods)
        self.assertIn("DummyWorkflow::methodAnnotatedPlain", worker.workflow_methods)
        self.assertIn("DummyWorkflow::method_annotated_decorator_call", worker.workflow_methods)
        self.assertIn("DummyWorkflow::methodAnnotatedDecoratorCall", worker.workflow_methods)
        self.assertIn("NAME", worker.workflow_methods)

        (cls, fn) = worker.workflow_methods.get("DummyWorkflow::method_annotated_plain")
        self.assertEqual(DummyWorkflow, cls)
        self.assertEqual(fn, DummyWorkflow.method_annotated_plain)


class TestNewActivityStub(TestCase):

    def setUp(self) -> None:
        pass

    def test_new_activity_stub(self):
        class Activities:
            def do_stuff(self):
                pass

        workflow_task: WorkflowTask = Mock()
        workflow_task.decider = Mock()
        workflow_task.decider.decision_context = Mock()
        current_workflow_task.set(workflow_task)
        stub = Workflow.new_activity_stub(Activities)
        self.assertEqual(workflow_task.decider.decision_context, stub._decision_context)
