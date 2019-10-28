import json
import os
from typing import List
from unittest import TestCase
from unittest.mock import Mock, MagicMock

from cadence.cadence_types import HistoryEvent, EventType, PollForDecisionTaskResponse, \
    ScheduleActivityTaskDecisionAttributes, WorkflowExecutionStartedEventAttributes, Decision, \
    ActivityTaskStartedEventAttributes
from cadence.decision_loop import HistoryHelper, is_decision_event, DecisionTaskLoop, ReplayDecider, DecisionEvents, \
    nano_to_milli
from cadence.decisions import DecisionId, DecisionTarget
from cadence.exceptions import NonDeterministicWorkflowException
from cadence.state_machines import ActivityDecisionStateMachine, DecisionStateMachine
from cadence.tests import init_test_logging
from cadence.tests.utils import json_to_data_class
from cadence.worker import Worker
from cadence.workflow import workflow_method

__location__ = os.path.dirname(__file__)

init_test_logging()


def make_history(event_types: List[EventType]) -> List[HistoryEvent]:
    history = []
    for offset, event_type in enumerate(event_types):
        history.append(HistoryEvent(event_id=offset + 1, event_type=event_type, timestamp=0))
    return history


class TestHistoryHelper(TestCase):

    def setUp(self) -> None:
        self.events = make_history([
            EventType.WorkflowExecutionStarted,
            EventType.DecisionTaskScheduled,
            EventType.DecisionTaskStarted,
            EventType.DecisionTaskCompleted,
            EventType.ActivityTaskScheduled,
            EventType.ActivityTaskStarted,
            EventType.ActivityTaskCompleted,
            EventType.DecisionTaskScheduled,
            EventType.DecisionTaskStarted,
            EventType.DecisionTaskCompleted,
            EventType.ActivityTaskScheduled,
            EventType.ActivityTaskStarted,
            EventType.ActivityTaskCompleted,
            EventType.DecisionTaskScheduled,
            EventType.DecisionTaskStarted
        ])

    def test_has_next(self):
        helper = HistoryHelper(self.events)
        self.assertTrue(helper.has_next())
        helper.next()
        self.assertTrue(helper.has_next())
        helper.next()
        self.assertTrue(helper.has_next())
        helper.next()
        self.assertFalse(helper.has_next())

    def test_decision_event(self):
        helper = HistoryHelper(self.events)
        self.assertTrue(helper.has_next())

        expected_decisions = [
            ([EventType.WorkflowExecutionStarted, EventType.DecisionTaskScheduled],
             [EventType.ActivityTaskScheduled]),
            ([EventType.ActivityTaskStarted, EventType.ActivityTaskCompleted, EventType.DecisionTaskScheduled],
             [EventType.ActivityTaskScheduled]),
            ([EventType.ActivityTaskStarted, EventType.ActivityTaskCompleted, EventType.DecisionTaskScheduled],
             []),
        ]

        for expected_events, expected_decision_events in expected_decisions:
            e = helper.next()
            self.assertEqual(expected_events, list(map(lambda x: x.event_type, e.events)))
            self.assertEqual(expected_decision_events, list(map(lambda x: x.event_type, e.decision_events)))

    def test_replay(self):
        helper = HistoryHelper(self.events)
        e = helper.next()
        self.assertTrue(e.replay)
        e = helper.next()
        self.assertTrue(e.replay)
        e = helper.next()
        self.assertFalse(e.replay)

    def test_next_decision_event_id(self):
        helper = HistoryHelper(self.events)
        e = helper.next()
        self.assertEqual(5, e.next_decision_event_id)
        e = helper.next()
        self.assertEqual(11, e.next_decision_event_id)
        e = helper.next()
        self.assertEqual(17, e.next_decision_event_id)


class TestIsDecisionEvent(TestCase):
    def test_true(self):
        event = HistoryEvent(event_type=EventType.ActivityTaskScheduled)
        self.assertTrue(is_decision_event(event))

    def test_false(self):
        event = HistoryEvent(event_type=EventType.WorkflowExecutionStarted)
        self.assertFalse(is_decision_event(event))


class TestDecisionTaskLoop(TestCase):
    def setUp(self) -> None:
        fp = open(os.path.join(__location__, "workflow_started_decision_task_response.json"))
        self.poll_response: PollForDecisionTaskResponse = json_to_data_class(json.loads(fp.read()),
                                                                             PollForDecisionTaskResponse)
        fp.close()
        self.worker = Worker()
        self.loop = DecisionTaskLoop(worker=self.worker)
        global dummy_workflow_self
        dummy_workflow_self = None

    def test_create_workflow_object(self):
        class DummyWorkflow:
            @workflow_method()
            async def dummy(self):
                nonlocal dummy_workflow_self
                dummy_workflow_self = self

        dummy_workflow_self = None
        self.worker.register_workflow_implementation_type(DummyWorkflow)
        self.loop.process_task(self.poll_response)
        self.assertIsInstance(dummy_workflow_self, DummyWorkflow)

    def test_return_none(self):
        class DummyWorkflow:
            @workflow_method()
            async def dummy(self):
                return None

        self.worker.register_workflow_implementation_type(DummyWorkflow)
        decisions = self.loop.process_task(self.poll_response)
        complete_workflow = decisions[0].complete_workflow_execution_decision_attributes
        self.assertEqual("null", complete_workflow.result)

    def test_args(self):
        class DummyWorkflow:
            @workflow_method()
            async def dummy(self, arg1, arg2):
                nonlocal arg1_value, arg2_value
                arg1_value = arg1
                arg2_value = arg2

        arg1_value = None
        arg2_value = None
        self.worker.register_workflow_implementation_type(DummyWorkflow)
        self.poll_response.history.events[0].workflow_execution_started_event_attributes.input = json.dumps(
            ["first", "second"])
        self.loop.process_task(self.poll_response)
        self.assertEqual(arg1_value, "first")
        self.assertEqual(arg2_value, "second")

    def test_no_args(self):
        class DummyWorkflow:
            @workflow_method()
            async def dummy(self):
                nonlocal executed
                executed = True

        executed = False
        self.worker.register_workflow_implementation_type(DummyWorkflow)
        self.poll_response.history.events[0].workflow_execution_started_event_attributes.input = json.dumps([])
        self.loop.process_task(self.poll_response)
        self.assertTrue(executed)

    def test_return_value(self):
        class DummyWorkflow:
            @workflow_method()
            async def dummy(self):
                return "value"

        self.worker.register_workflow_implementation_type(DummyWorkflow)
        decisions = self.loop.process_task(self.poll_response)
        complete_workflow = decisions[0].complete_workflow_execution_decision_attributes
        self.assertEqual('"value"', complete_workflow.result)


class TestScheduleActivityTask(TestCase):
    def setUp(self) -> None:
        self.decider = ReplayDecider(execution_id="", workflow_type=Mock(), worker=Mock())

    def test_schedule_activity_task(self):
        schedule_attributes = ScheduleActivityTaskDecisionAttributes()
        self.decider.schedule_activity_task(schedule_attributes)
        expected_decision_id = DecisionId(DecisionTarget.ACTIVITY, 0)
        self.assertEqual(1, self.decider.next_decision_event_id)
        self.assertEqual(1, len(self.decider.decisions))
        state_machine: ActivityDecisionStateMachine = self.decider.decisions[expected_decision_id]
        self.assertIs(schedule_attributes, state_machine.schedule_attributes)
        self.assertEqual(expected_decision_id, state_machine.id)

    def test_activity_id(self):
        activity_id = 20
        schedule_attributes = ScheduleActivityTaskDecisionAttributes()
        schedule_attributes.activity_id = activity_id
        self.decider.schedule_activity_task(schedule_attributes)
        self.assertEqual(0, self.decider.activity_id_to_scheduled_event_id[activity_id])


class DummyWorkflow:
    pass


class TestDecideNextDecisionId(TestCase):
    def setUp(self) -> None:
        events = make_history([
            EventType.WorkflowExecutionStarted,
            EventType.DecisionTaskScheduled,
            EventType.DecisionTaskStarted])
        events[0].workflow_execution_started_event_attributes = WorkflowExecutionStartedEventAttributes()
        helper = HistoryHelper(events)
        self.decision_events = helper.next()
        worker: Worker = Mock()
        worker.get_workflow_method = MagicMock(return_value=(DummyWorkflow, lambda *args: None))
        self.decider = ReplayDecider(execution_id="", workflow_type=Mock(), worker=worker)
        self.decider.event_loop = Mock()

    def test_first_decision_next_decision_id(self):
        self.decider.process_decision_events(self.decision_events)
        self.assertEqual(5, self.decider.next_decision_event_id)


class ReplayDeciderDestroyTest(TestCase):

    def setUp(self) -> None:
        self.workflow_task = Mock()
        self.decider = ReplayDecider(execution_id="", workflow_type=Mock(), worker=Mock())
        self.decider.workflow_task = self.workflow_task

    def test_destroy(self):
        self.decider.destroy()
        self.workflow_task.destroy.assert_called()


class TestReplayDecider(TestCase):

    def setUp(self) -> None:
        worker: Worker = Mock()
        worker.get_workflow_method = MagicMock(return_value=(DummyWorkflow, lambda *args: None))
        self.decider = ReplayDecider(execution_id="", workflow_type=Mock(), worker=worker)

    def test_get_and_increment_next_id(self):
        self.assertEqual("0", self.decider.get_and_increment_next_id())
        self.assertEqual("1", self.decider.get_and_increment_next_id())

    def test_get_decisions(self):
        decision = Decision()
        state_machine: DecisionStateMachine = Mock()
        state_machine.get_decision = MagicMock(return_value=decision)
        self.decider.decisions[DecisionId(DecisionTarget.ACTIVITY, 10)] = state_machine
        decisions = self.decider.get_decisions()
        self.assertEqual(1, len(decisions))
        self.assertIs(decision, decisions[0])

    def test_get_decisions_none(self):
        state_machine: DecisionStateMachine = Mock()
        state_machine.get_decision = MagicMock(return_value=None)
        self.decider.decisions[DecisionId(DecisionTarget.ACTIVITY, 10)] = state_machine
        decisions = self.decider.get_decisions()
        self.assertEqual(0, len(decisions))

    def test_get_decision(self):
        state_machine = DecisionStateMachine()
        decision_id = DecisionId(DecisionTarget.ACTIVITY, 20)
        self.decider.decisions[decision_id] = state_machine
        self.assertIs(state_machine, self.decider.get_decision(decision_id))

    def test_get_decision_not_found(self):
        decision_id = DecisionId(DecisionTarget.ACTIVITY, 20)
        with self.assertRaises(NonDeterministicWorkflowException):
            self.decider.get_decision(decision_id)

    def test_notify_decision_sent(self):
        state_machine: DecisionStateMachine = Mock()
        self.decider.decisions[DecisionId(DecisionTarget.ACTIVITY, 10)] = state_machine
        self.decider.notify_decision_sent()
        state_machine.handle_decision_task_started_event.assert_called_once()

    def test_process_decision_events_notifies_when_replay(self):
        self.decider.event_loop = Mock()
        events = [
            HistoryEvent(event_type=EventType.WorkflowExecutionStarted,
                         workflow_execution_started_event_attributes=WorkflowExecutionStartedEventAttributes()),
            HistoryEvent(event_type=EventType.DecisionTaskScheduled)
        ]
        decision_events = DecisionEvents(events, [], replay=True,
                                         replay_current_time_milliseconds=0,
                                         next_decision_event_id=5)
        self.decider.notify_decision_sent = MagicMock()
        self.decider.process_decision_events(decision_events)
        self.decider.notify_decision_sent.assert_called_once()

    def test_activity_task_closed(self):
        state_machine: DecisionStateMachine = Mock()
        state_machine.is_done = MagicMock(return_value=True)
        self.decider.decisions[DecisionId(DecisionTarget.ACTIVITY, 10)] = state_machine
        ret = self.decider.handle_activity_task_closed(10)
        self.assertTrue(ret)
        state_machine.handle_completion_event.assert_called_once()
        state_machine.is_done.assert_called_once()

    def test_handle_activity_task_scheduled(self):
        state_machine: DecisionStateMachine = Mock()
        self.decider.decisions[DecisionId(DecisionTarget.ACTIVITY, 10)] = state_machine
        event = HistoryEvent(event_id=10)
        self.decider.handle_activity_task_scheduled(event)
        state_machine.handle_initiated_event.assert_called()
        args, kwargs = state_machine.handle_initiated_event.call_args_list[0]
        self.assertIn(event, args)

    def test_handle_activity_task_started(self):
        state_machine: DecisionStateMachine = Mock()
        self.decider.decisions[DecisionId(DecisionTarget.ACTIVITY, 10)] = state_machine
        event = HistoryEvent(event_id=15)
        event.activity_task_started_event_attributes = ActivityTaskStartedEventAttributes()
        event.activity_task_started_event_attributes.scheduled_event_id = 10
        self.decider.handle_activity_task_started(event)
        state_machine.handle_started_event.assert_called()
        args, kwargs = state_machine.handle_started_event.call_args_list[0]
        self.assertIn(event, args)

    def tearDown(self) -> None:
        self.decider.destroy()


def test_nano_to_milli():
    assert 1 == nano_to_milli(1000000)
    assert 1000 == nano_to_milli(1e9)
