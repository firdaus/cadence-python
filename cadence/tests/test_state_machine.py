from unittest import TestCase

from cadence.cadence_types import ScheduleActivityTaskDecisionAttributes, DecisionType, HistoryEvent, Decision
from cadence.decisions import DecisionId, DecisionTarget, DecisionState
from cadence.exceptions import IllegalStateException
from cadence.state_machines import DecisionStateMachineBase, ActivityDecisionStateMachine, CompleteWorkflowStateMachine


class DecisionStateMachineBaseTest(TestCase):

    def setUp(self) -> None:
        self.state_machine = DecisionStateMachineBase(DecisionId(DecisionTarget.ACTIVITY, 123))

    def test_initial_state(self):
        self.assertEqual(DecisionState.CREATED, self.state_machine.get_state())

    def test_get_id(self):
        self.assertEqual(DecisionId(DecisionTarget.ACTIVITY, 123), self.state_machine.get_id())

    def test_is_done_created(self):
        self.assertFalse(self.state_machine.is_done())

    def test_is_done_completed(self):
        self.state_machine.state = DecisionState.COMPLETED
        self.assertTrue(self.state_machine.is_done())

    def test_handle_decision_task_started_event(self):
        self.state_machine.handle_decision_task_started_event()
        self.assertTrue(DecisionState.DECISION_SENT, self.state_machine.state)

    def test_cancel_create(self):
        def fn():
            nonlocal called
            called = True

        called = False
        self.state_machine.cancel(fn)
        self.assertTrue(called)
        self.assertEqual(DecisionState.COMPLETED, self.state_machine.state)

    def test_cancel_decision_sent(self):
        self.state_machine.state = DecisionState.DECISION_SENT
        self.state_machine.cancel(None)
        self.assertEqual(DecisionState.CANCELED_BEFORE_INITIATED, self.state_machine.state)

    def test_cancel_initiated(self):
        self.state_machine.state = DecisionState.INITIATED
        self.state_machine.cancel(None)
        self.assertEqual(DecisionState.CANCELED_AFTER_INITIATED, self.state_machine.state)

    def test_handle_initiated_event_decision_sent(self):
        self.state_machine.state = DecisionState.DECISION_SENT
        self.state_machine.handle_initiated_event(HistoryEvent())
        self.assertEqual(DecisionState.INITIATED, self.state_machine.state)

    def test_handle_initiated_event_canceled_before_initiated(self):
        self.state_machine.state = DecisionState.CANCELED_BEFORE_INITIATED
        self.state_machine.handle_initiated_event(HistoryEvent())
        self.assertEqual(DecisionState.CANCELED_AFTER_INITIATED, self.state_machine.state)

    def test_handle_initiation_failed_event(self):
        for state in (DecisionState.INITIATED, DecisionState.DECISION_SENT, DecisionState.CANCELED_BEFORE_INITIATED):
            self.state_machine.state = state
            self.state_machine.handle_initiation_failed_event(HistoryEvent())
            self.assertEqual(DecisionState.COMPLETED, self.state_machine.state)

    def test_handled_started_event(self):
        self.state_machine.handle_started_event(HistoryEvent())

    def test_handle_completion_event_canceled_initiated(self):
        for state in (DecisionState.CANCELED_AFTER_INITIATED, DecisionState.INITIATED):
            self.state_machine.state = state
            self.state_machine.handle_completion_event()
            self.assertEqual(DecisionState.COMPLETED, self.state_machine.state)

    def test_handle_completion_event_cancellation_decision_sent(self):
        self.state_machine.state = DecisionState.CANCELLATION_DECISION_SENT
        self.state_machine.handle_completion_event()
        self.assertEqual(DecisionState.COMPLETED_AFTER_CANCELLATION_DECISION_SENT, self.state_machine.state)

    def test_handle_cancellation_initiated_event(self):
        self.state_machine.state = DecisionState.CANCELLATION_DECISION_SENT
        self.state_machine.handle_cancellation_initiated_event()
        self.assertEqual(DecisionState.CANCELLATION_DECISION_SENT, self.state_machine.state)

    def test_handle_cancellation_failure_event(self):
        self.state_machine.state = DecisionState.COMPLETED_AFTER_CANCELLATION_DECISION_SENT
        self.state_machine.handle_cancellation_failure_event(HistoryEvent())
        self.assertEqual(DecisionState.COMPLETED, self.state_machine.state)

    def test_handle_cancellation_event(self):
        self.state_machine.state = DecisionState.CANCELLATION_DECISION_SENT
        self.state_machine.handle_cancellation_event()
        self.assertEqual(DecisionState.COMPLETED, self.state_machine.state)

    def test_fail_state_transition(self):
        with self.assertRaises(IllegalStateException):
            self.state_machine.fail_state_transition()


class ActivityDecisionStateMachineTest(TestCase):
    def setUp(self) -> None:
        self.schedule_attributes = ScheduleActivityTaskDecisionAttributes()
        self.schedule_attributes.activity_id = "123"
        self.state_machine: ActivityDecisionStateMachine = ActivityDecisionStateMachine(
            DecisionId(DecisionTarget.ACTIVITY, 888), schedule_attributes=self.schedule_attributes)

    def test_get_decision_created(self):
        self.state_machine.state = DecisionState.CREATED
        decision = self.state_machine.get_decision()
        self.assertEqual(DecisionType.ScheduleActivityTask, decision.decision_type)
        self.assertIs(self.schedule_attributes, decision.schedule_activity_task_decision_attributes)

    def test_get_decision_canceled_after_initiated(self):
        self.state_machine.state = DecisionState.CANCELED_AFTER_INITIATED
        decision = self.state_machine.get_decision()
        self.assertEqual(DecisionType.RequestCancelActivityTask, decision.decision_type)
        self.assertEqual("123", decision.request_cancel_activity_task_decision_attributes.activity_id)

    def test_handle_decision_task_started_event(self):
        self.state_machine.state = DecisionState.CANCELED_AFTER_INITIATED
        self.state_machine.handle_decision_task_started_event()
        self.assertEqual(DecisionState.CANCELLATION_DECISION_SENT, self.state_machine.state)

    def test_handle_decision_task_started_event_created(self):
        self.state_machine.state = DecisionState.CREATED
        self.state_machine.handle_decision_task_started_event()
        self.assertEqual(DecisionState.DECISION_SENT, self.state_machine.state)

    def test_handle_cancellation_failure_event(self):
        self.state_machine.state = DecisionState.CANCELLATION_DECISION_SENT
        self.state_machine.handle_cancellation_failure_event(HistoryEvent())
        self.assertEqual(DecisionState.INITIATED, self.state_machine.state)

    def test_handle_cancellation_failure_event_completed_after_cancellation_decision_sent(self):
        self.state_machine.state = DecisionState.COMPLETED_AFTER_CANCELLATION_DECISION_SENT
        self.state_machine.handle_cancellation_failure_event(HistoryEvent())
        self.assertEqual(DecisionState.COMPLETED, self.state_machine.state)


class CompleteWorkflowStateMachineTest(TestCase):
    def setUp(self) -> None:
        self.decision_id = DecisionId(DecisionTarget.SELF, 256)
        self.decision = Decision()
        self.state_machine = CompleteWorkflowStateMachine(self.decision_id, self.decision)

    def test_get_id(self):
        self.assertIs(self.decision_id, self.state_machine.get_id())

    def test_get_decision(self):
        self.assertIs(self.decision, self.state_machine.get_decision())

    def test_handle_initiation_failed_event(self):
        self.state_machine.handle_initiation_failed_event(HistoryEvent())
        self.assertIsNone(self.state_machine.get_decision())

    def test_get_state(self):
        self.assertEqual(DecisionState.CREATED, self.state_machine.get_state())

    def test_is_done(self):
        self.assertTrue(self.state_machine.is_done())

    def test_handle_decision_tast_started_event(self):
        self.state_machine.handle_decision_task_started_event()
