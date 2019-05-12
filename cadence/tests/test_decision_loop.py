from typing import List
from unittest import TestCase

from cadence.cadence_types import HistoryEvent, EventType
from cadence.decision_loop import HistoryHelper, is_decision_event


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

