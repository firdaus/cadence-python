import asyncio
import json
from _asyncio import Future
from asyncio import AbstractEventLoop
from unittest import TestCase
from unittest.mock import Mock, MagicMock

from cadence.activity_method import ExecuteActivityParameters
from cadence.cadence_types import ActivityType, ScheduleActivityTaskDecisionAttributes, HistoryEvent, EventType, \
    ActivityTaskCompletedEventAttributes, ActivityTaskFailedEventAttributes, ActivityTaskTimedOutEventAttributes, \
    TimeoutType
from cadence.decision_loop import DecisionContext, ReplayDecider
from cadence.exceptions import NonDeterministicWorkflowException, ActivityTaskFailedException, \
    ActivityTaskTimeoutException


def run_once(loop):
    loop.call_soon(loop.stop)
    loop.run_forever()


class TestScheduleActivity(TestCase):

    def setUp(self) -> None:
        self.event_loop: AbstractEventLoop = asyncio.get_event_loop()
        self.decider: ReplayDecider = Mock()
        self.decider.get_and_increment_next_id = MagicMock(return_value="0")
        self.decider.event_loop = Mock()
        self.future = self.event_loop.create_future()
        self.decider.event_loop.create_future = MagicMock(return_value=self.future)
        self.context = DecisionContext(decider=self.decider)
        self.params = ExecuteActivityParameters()
        self.params.input = bytes(json.dumps([1, 2, 3]), "utf-8")
        self.params.heartbeat_timeout_seconds = 10
        self.params.schedule_to_close_timeout_seconds = 20
        self.params.schedule_to_start_timeout_seconds = 30
        self.params.start_to_close_timeout_seconds = 40
        self.params.activity_type = ActivityType()
        self.params.activity_type.name = "Activity::activity"
        self.params.task_list = "the-task-list"

    def test_schedule(self):
        self.task = self.event_loop.create_task(self.context.schedule_activity_task(self.params))
        run_once(self.event_loop)
        self.assertEqual(1, len(self.context.scheduled_activities))
        self.decider.schedule_activity_task.assert_called_once()
        args, kwargs = self.decider.schedule_activity_task.call_args_list[0]
        attr: ScheduleActivityTaskDecisionAttributes = kwargs["schedule"]
        self.assertEqual("Activity::activity", attr.activity_type.name)
        self.assertEqual("the-task-list", attr.task_list.name)
        self.assertEqual(b"[1, 2, 3]", attr.input)
        self.assertEqual(10, attr.heartbeat_timeout_seconds)
        self.assertEqual(20, attr.schedule_to_close_timeout_seconds)
        self.assertEqual(30, attr.schedule_to_start_timeout_seconds)
        self.assertEqual(40, attr.start_to_close_timeout_seconds)
        self.assertEqual("0", attr.activity_id)

    def test_custom_activity_id(self):
        self.params.activity_id = "20"
        self.task = self.event_loop.create_task(self.context.schedule_activity_task(self.params))
        run_once(self.event_loop)
        args, kwargs = self.decider.schedule_activity_task.call_args_list[0]
        attr: ScheduleActivityTaskDecisionAttributes = kwargs["schedule"]
        self.assertEqual("20", attr.activity_id)

    def test_return_value(self):
        self.decider.schedule_activity_task = MagicMock(return_value=20)
        self.task = self.event_loop.create_task(self.context.schedule_activity_task(self.params))

        run_once(self.event_loop)
        self.assertFalse(self.task.done())
        future = self.context.scheduled_activities[20]
        self.assertIs(self.future, future)

        activity_ret_value = {"name": "this-is-python"}
        future.set_result(bytes(json.dumps(activity_ret_value), "utf-8"))
        run_once(self.event_loop)
        self.assertTrue(self.task.done())
        result = self.task.result()
        self.assertEqual(result, activity_ret_value)

    def test_raise_exception(self):
        self.decider.schedule_activity_task = MagicMock(return_value=20)
        self.task = self.event_loop.create_task(self.context.schedule_activity_task(self.params))

        run_once(self.event_loop)
        self.assertFalse(self.task.done())

        future = self.context.scheduled_activities[20]
        exception = Exception("thrown by activity")
        future.set_exception(exception)
        run_once(self.event_loop)
        self.assertTrue(self.task.done())

        raised_exception = self.task.exception()
        self.assertEqual(exception, raised_exception)

    def tearDown(self) -> None:
        self.task.cancel()


class TestHandleActivityTaskEvents(TestCase):
    def setUp(self) -> None:
        self.decider: ReplayDecider = Mock()
        self.decider.handle_activity_task_closed = MagicMock(return_value=True)
        self.context = DecisionContext(decider=self.decider)
        self.future: Future = Future()
        self.context.scheduled_activities[20] = self.future

    def test_handle_activity_task_completed(self):
        event = HistoryEvent(event_type=EventType.ActivityTaskCompleted)
        attr = ActivityTaskCompletedEventAttributes()
        self.payload = {"name": "bob"}
        attr.scheduled_event_id = 20
        attr.result = bytes(json.dumps(self.payload), "utf-8")
        event.activity_task_completed_event_attributes = attr
        self.context.handle_activity_task_completed(event)
        self.assertTrue(self.future.done())
        result = self.future.result()
        self.assertIs(attr.result, result)
        self.assertEqual(0, len(self.context.scheduled_activities))

    def test_non_deterministic(self):
        event = HistoryEvent(event_type=EventType.ActivityTaskCompleted)
        attr = ActivityTaskCompletedEventAttributes()
        attr.scheduled_event_id = 9999
        event.activity_task_completed_event_attributes = attr
        with self.assertRaises(NonDeterministicWorkflowException):
            self.context.handle_activity_task_completed(event)
        self.assertFalse(self.future.done())

    def test_activity_task_failed(self):
        event = HistoryEvent(event_type=EventType.ActivityTaskFailed)
        attr = ActivityTaskFailedEventAttributes()
        attr.scheduled_event_id = 20
        event.activity_task_failed_event_attributes = attr
        attr.reason = "the-reason"
        attr.details = bytes("details", "utf-8")
        self.context.handle_activity_task_failed(event)
        self.assertTrue(self.future.done())
        exception = self.future.exception()
        self.assertIsInstance(exception, ActivityTaskFailedException)
        self.assertEqual(attr.reason, exception.reason)
        self.assertEqual(attr.details, exception.details)
        self.assertEqual(0, len(self.context.scheduled_activities))

    def test_activity_task_timed_out(self):
        event = HistoryEvent(event_type=EventType.ActivityTaskTimedOut)
        event.event_id = 25
        attr = ActivityTaskTimedOutEventAttributes()
        attr.scheduled_event_id = 20
        attr.details = bytes("details", "utf-8")
        attr.timeout_type = TimeoutType.HEARTBEAT
        event.activity_task_timed_out_event_attributes = attr
        self.context.handle_activity_task_timed_out(event)
        self.assertTrue(self.future.done())
        exception = self.future.exception()
        self.assertIsInstance(exception, ActivityTaskTimeoutException)
        self.assertEqual(event.event_id, exception.event_id)
        self.assertEqual(attr.timeout_type, exception.timeout_type)
        self.assertEqual(attr.details, exception.details)
        self.assertEqual(0, len(self.context.scheduled_activities))


class TestAwaitTill(TestCase):

    def setUp(self) -> None:
        self.event_loop: AbstractEventLoop = asyncio.get_event_loop()
        self.decider: ReplayDecider = Mock()
        self.decider.get_and_increment_next_id = MagicMock(return_value="0")
        self.decider.event_loop = Mock()
        self.future = self.event_loop.create_future()
        self.decider.event_loop.create_future = MagicMock(return_value=self.future)
        self.context = DecisionContext(decider=self.decider)

    def tearDown(self) -> None:
        self.task.cancel()

    def test_await_till(self):
        self.task = self.event_loop.create_task(self.context.await_till())
        run_once(self.event_loop)
        assert self.context.awaited

    def test_await_till_no_progress(self):
        self.task = self.event_loop.create_task(self.context.await_till())
        run_once(self.event_loop)
        assert self.context.awaited
        run_once(self.event_loop)
        assert self.context.awaited

    def test_unblock(self):
        self.task = self.event_loop.create_task(self.context.await_till())
        run_once(self.event_loop)
        self.context.unblock()
        run_once(self.event_loop)
        assert not self.context.awaited
