import unittest

from cadence.thread import WorkflowThreadContext, WorkflowThread, current_workflow_thread, Status
from cadence.exceptions import DestroyWorkflowThreadError


class DummyException(Exception):
    pass


class TestWorkflowThread(unittest.TestCase):

    def setUp(self) -> None:
        self.context = WorkflowThreadContext()

    def test_init(self):
        self.assertIsNotNone(self.context.lock)
        self.assertIsNotNone(self.context.run_condition)
        self.assertIsNotNone(self.context.yield_condition)
        self.assertIsNotNone(self.context.evaluation_condition)

    def test_run(self):
        started = False

        def fn():
            nonlocal started
            started = True

        thread = WorkflowThread(workflow_proc=fn)
        thread.start()
        thread.context.run_until_blocked()

        self.assertTrue(started)
        self.assertTrue(thread.thread)

    def test_done(self):
        def fn():
            pass

        thread = WorkflowThread(workflow_proc=fn)
        thread.start()
        thread.context.run_until_blocked()

        self.assertTrue(thread.context.is_done())

    def test_context_var(self):
        ran = False
        var = None
        current = None

        def fn():
            nonlocal thread, ran, var, current
            var = current_workflow_thread.get()
            current = WorkflowThread.current()
            ran = True

        thread = WorkflowThread(workflow_proc=fn)
        thread.start()
        thread.context.run_until_blocked()
        self.assertTrue(ran)
        self.assertEqual(thread, var)
        self.assertEqual(thread, current)

    def test_run_until_blocked_with_yield(self):
        completed = False

        def fn():
            nonlocal completed
            WorkflowThread.current().context.yield_thread("dummy", lambda: completed)

        thread = WorkflowThread(workflow_proc=fn)
        thread.start()
        thread.context.run_until_blocked()
        self.assertEqual(Status.YIELDED, thread.context.get_status())
        completed = True
        thread.context.run_until_blocked()
        self.assertEqual(Status.DONE, thread.context.get_status())

    def test_destroy(self):
        ended = False
        destroy_exception_raised = False

        def fn():
            nonlocal ended, destroy_exception_raised
            try:
                WorkflowThread.current().context.yield_thread("dummy", lambda: False)
            except DestroyWorkflowThreadError as ex:
                destroy_exception_raised = True
                raise ex
            ended = True

        thread = WorkflowThread(workflow_proc=fn)
        thread.start()
        thread.context.run_until_blocked()
        thread.context.destroy()
        self.assertTrue(destroy_exception_raised)
        self.assertTrue(thread.context.destroy_requested)
        self.assertFalse(ended)
        self.assertEqual(Status.DONE, thread.context.get_status())

    def test_initial_yield(self):
        started = False

        def fn():
            nonlocal started
            started = True

        thread = WorkflowThread(workflow_proc=fn)
        thread.start()
        self.assertEqual(Status.YIELDED, thread.context.get_status())
        self.assertFalse(started)
        thread.context.run_until_blocked()
        self.assertTrue(started)

    def test_resume_before_unblock(self):
        completed = False
        ended = False

        def fn():
            nonlocal completed, ended
            WorkflowThread.current().context.yield_thread("dummy", lambda: completed)
            ended = True

        thread = WorkflowThread(workflow_proc=fn)
        thread.start()
        thread.context.run_until_blocked()
        self.assertFalse(ended)
        thread.context.run_until_blocked()
        self.assertFalse(ended)
        completed = True
        thread.context.run_until_blocked()
        self.assertTrue(ended)

    def test_evaluate_in_coroutine_context(self):
        exception_thrown = False
        eval_function_called_count = 0

        def throw_exception(*args):
            nonlocal eval_function_called_count
            eval_function_called_count += 1
            raise DummyException()

        def fn():
            nonlocal exception_thrown
            try:
                WorkflowThread.current().context.yield_thread("dummy", lambda: False)
            except DummyException as ex:
                exception_thrown = True

        thread = WorkflowThread(workflow_proc=fn)
        thread.start()
        thread.context.run_until_blocked()
        thread.context.evaluate_in_coroutine_context(throw_exception)
        self.assertTrue(exception_thrown)
        self.assertEqual(2, eval_function_called_count)
        self.assertEqual(Status.DONE, thread.context.get_status())

    def test_running(self):
        status_in_thread = None

        def fn():
            nonlocal status_in_thread
            status_in_thread = WorkflowThread.current().context.get_status()

        thread = WorkflowThread(workflow_proc=fn)
        thread.start()
        thread.context.run_until_blocked()
        self.assertTrue(Status.RUNNING, status_in_thread)

    def test_get_unhandled_exception(self):
        ex = DummyException("test")

        def fn():
            raise ex

        thread = WorkflowThread(workflow_proc=fn)
        thread.start()
        thread.context.run_until_blocked()

        self.assertEqual(ex, thread.context.get_unhandled_exception())
