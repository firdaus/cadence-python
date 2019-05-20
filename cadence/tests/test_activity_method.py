from unittest import TestCase
from unittest.mock import Mock

from cadence.activity_method import activity_method, ExecuteActivityParameters
from cadence.decision_loop import DecisionContext


class ActivityMethodTest(TestCase):

    def test_no_paren(self):
        with self.assertRaisesRegex(Exception, "activity_method must be called with arguments"):
            class HelloActivities:
                @activity_method
                def hello(self):
                    pass

    def test_no_task_list(self):
        with self.assertRaisesRegex(Exception, "task_list parameter is mandatory"):
            class HelloActivities:
                @activity_method()
                def hello(self):
                    pass

    def test_default_name(self):
        class HelloActivities:
            @activity_method(task_list="test-tasklist")
            def hello(self):
                pass

        self.assertEqual("HelloActivities::hello", HelloActivities.hello._execute_parameters.activity_type.name)

    def test_name_provided(self):
        class HelloActivities:
            @activity_method(name="custom-name", task_list="test-tasklist")
            def hello(self):
                pass

        self.assertEqual("custom-name", HelloActivities.hello._execute_parameters.activity_type.name)

    def test_task_list(self):
        class HelloActivities:
            @activity_method(task_list="test-tasklist")
            def hello(self):
                pass

        self.assertEqual("test-tasklist", HelloActivities.hello._execute_parameters.task_list)

    def test_timeouts(self):
        class HelloActivities:
            @activity_method(schedule_to_close_timeout_seconds=1,
                             schedule_to_start_timeout_seconds=2,
                             start_to_close_timeout_seconds=3,
                             heartbeat_timeout_seconds=4,
                             task_list="test-tasklist")
            def hello(self):
                pass
        HelloActivities.hello._execute_parameters: ExecuteActivityParameters
        self.assertEqual(1, HelloActivities.hello._execute_parameters.schedule_to_close_timeout_seconds)
        self.assertEqual(2, HelloActivities.hello._execute_parameters.schedule_to_start_timeout_seconds)
        self.assertEqual(3, HelloActivities.hello._execute_parameters.start_to_close_timeout_seconds)
        self.assertEqual(4, HelloActivities.hello._execute_parameters.heartbeat_timeout_seconds)

    def test_invoke_stub_no_args(self):
        class HelloActivities:
            @activity_method(task_list="test-tasklist")
            def hello(self):
                pass
        decision_context: DecisionContext = Mock()
        stub = HelloActivities()
        stub._decision_context= decision_context
        stub.hello()
        decision_context.schedule_activity_task.assert_called_once()
        args, kwargs = decision_context.schedule_activity_task.call_args_list[0]
        self.assertEqual(b"null", kwargs["parameters"].input)

    def test_invoke_stub_with_args(self):
        class HelloActivities:
            @activity_method(task_list="test-tasklist")
            def hello(self, arg1, arg2):
                pass
        decision_context: DecisionContext = Mock()
        stub = HelloActivities()
        stub._decision_context= decision_context
        stub.hello(1, "one")
        decision_context.schedule_activity_task.assert_called_once()
        args, kwargs = decision_context.schedule_activity_task.call_args_list[0]
        self.assertEqual(b'[1, "one"]', kwargs["parameters"].input)
