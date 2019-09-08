import pytest

from cadence.cadence_types import StartTimerDecisionAttributes, DecisionType, HistoryEvent
from cadence.decisions import DecisionState
from cadence.exceptions import IllegalArgumentException
from cadence.state_machines import TimerDecisionStateMachine


@pytest.fixture
def timer_dsm() -> TimerDecisionStateMachine:
    attributes = StartTimerDecisionAttributes()
    attributes.timer_id = "the-timer-id"
    return TimerDecisionStateMachine(start_timer_attributes=attributes)


def test_exception_no_attributes():
    with pytest.raises(IllegalArgumentException):
        TimerDecisionStateMachine()


def test_init_with_attributes():
    TimerDecisionStateMachine(start_timer_attributes=StartTimerDecisionAttributes())


def test_get_decision_created(timer_dsm: TimerDecisionStateMachine):
    timer_dsm.state = DecisionState.CREATED
    decision = timer_dsm.get_decision()
    assert decision.decision_type == DecisionType.StartTimer


def test_get_decision_canceled_after_initiated(timer_dsm: TimerDecisionStateMachine):
    timer_dsm.state = DecisionState.CANCELED_AFTER_INITIATED
    decision = timer_dsm.get_decision()
    assert decision.decision_type == DecisionType.CancelTimer


def test_handle_decision_task_started_event(timer_dsm: TimerDecisionStateMachine):
    timer_dsm.state = DecisionState.CANCELED_AFTER_INITIATED
    timer_dsm.handle_decision_task_started_event()
    assert "handle_decision_task_started_event" in timer_dsm.state_history
    assert timer_dsm.state == DecisionState.CANCELLATION_DECISION_SENT
    assert str(DecisionState.CANCELLATION_DECISION_SENT) in timer_dsm.state_history


def test_handle_cancellation_failure_event(timer_dsm: TimerDecisionStateMachine):
    timer_dsm.state = DecisionState.CANCELLATION_DECISION_SENT
    timer_dsm.handle_cancellation_failure_event(HistoryEvent())
    assert "handle_cancellation_failure_event" in timer_dsm.state_history
    assert timer_dsm.state == DecisionState.INITIATED
    assert str(timer_dsm.state) in timer_dsm.state_history


def test_cancel(timer_dsm: TimerDecisionStateMachine):
    cb_called = False

    def cb():
        nonlocal cb_called
        cb_called = True

    timer_dsm.cancel(cb)
    assert timer_dsm.canceled
    assert cb_called
    assert "cancel" in timer_dsm.state_history


def test_is_done_default(timer_dsm: TimerDecisionStateMachine):
    assert not timer_dsm.is_done()


def test_is_done_completed(timer_dsm: TimerDecisionStateMachine):
    timer_dsm.state = DecisionState.COMPLETED
    assert timer_dsm.is_done()


def test_is_done_canceled(timer_dsm: TimerDecisionStateMachine):
    timer_dsm.canceled = True
    assert timer_dsm.is_done()


def test_create_cancel_timer_decision(timer_dsm: TimerDecisionStateMachine):
    d = timer_dsm.create_cancel_timer_decision()
    assert d.decision_type == DecisionType.CancelTimer
    assert d.cancel_timer_decision_attributes.timer_id == "the-timer-id"


def test_create_start_timer_decision(timer_dsm: TimerDecisionStateMachine):
    d = timer_dsm.create_start_timer_decision()
    assert d.decision_type == DecisionType.StartTimer
    assert d.start_timer_decision_attributes == timer_dsm.start_timer_attributes
