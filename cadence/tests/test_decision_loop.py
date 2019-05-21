import json
import os
from typing import List
from unittest import TestCase
from unittest.mock import Mock

from cadence.cadence_types import HistoryEvent, EventType, PollForDecisionTaskResponse, \
    ScheduleActivityTaskDecisionAttributes, WorkflowExecutionStartedEventAttributes
from cadence.decision_loop import HistoryHelper, is_decision_event, DecisionTaskLoop, ReplayDecider
from cadence.decisions import DecisionId, DecisionTarget
from cadence.state_machines import ActivityDecisionStateMachine
from cadence.tests import init_test_logging
from cadence.tests.utils import json_to_data_class
from cadence.worker import Worker
from cadence.workflow import workflow_method

__location__ = os.path.dirname(__file__)

init_test_logging()


def make_history(event_types: List[EventType]) -> List[HistoryEvent]:
    history = []
    for offset, event_type in enumerate(event_types):
        history.append(HistoryEvent(event_id=offset + 1, event_type=event_type))
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
            @workflow_method
            async def dummy(self):
                nonlocal dummy_workflow_self
                dummy_workflow_self = self

        dummy_workflow_self = None
        self.worker.register_workflow_implementation_type(DummyWorkflow)
        self.loop.process_task(self.poll_response)
        self.assertIsInstance(dummy_workflow_self, DummyWorkflow)

    def test_return_none(self):
        class DummyWorkflow:
            @workflow_method
            async def dummy(self):
                return None

        self.worker.register_workflow_implementation_type(DummyWorkflow)
        decisions = self.loop.process_task(self.poll_response)
        complete_workflow = decisions[0].complete_workflow_execution_decision_attributes
        self.assertEqual("null", complete_workflow.result)

    def test_args(self):
        class DummyWorkflow:
            @workflow_method
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
            @workflow_method
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
            @workflow_method
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


class TestDecideNextDecisionId(TestCase):
    def setUp(self) -> None:
        events = make_history([
            EventType.WorkflowExecutionStarted,
            EventType.DecisionTaskScheduled,
            EventType.DecisionTaskStarted])
        events[0].workflow_execution_started_event_attributes = WorkflowExecutionStartedEventAttributes()
        helper = HistoryHelper(events)
        self.decision_events = helper.next()
        self.decider = ReplayDecider(execution_id="", workflow_type=Mock(), worker=Mock())
        self.decider.event_loop = Mock()

    def test_first_decision_next_decision_id(self):
        self.decider.process_decision_events(self.decision_events)
        self.assertEqual(5, self.decider.next_decision_event_id)


class TestReplayDecider(TestCase):

    def setUp(self) -> None:
        self.decider = ReplayDecider(execution_id="", workflow_type=Mock(), worker=Mock())

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

    def test_get_decisions_null(self):
        state_machine: DecisionStateMachine = Mock()
        state_machine.get_decision = MagicMock(return_value=None)
        self.decider.decisions[DecisionId(DecisionTarget.ACTIVITY, 10)] = state_machine
        decisions = self.decider.get_decisions()
        self.assertEqual(0, len(decisions))

