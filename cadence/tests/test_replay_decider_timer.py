from unittest.mock import MagicMock, Mock

import pytest

from cadence.cadence_types import WorkflowType, StartTimerDecisionAttributes, TimerFiredEventAttributes, HistoryEvent, \
    TimerCanceledEventAttributes
from cadence.decision_loop import ReplayDecider, DecisionContext
from cadence.decisions import DecisionId, DecisionTarget, DecisionState
from cadence.state_machines import TimerDecisionStateMachine, DecisionStateMachine

DECISION_EVENT_ID = 55


@pytest.fixture
def decider():
    worker = MagicMock()
    decider = ReplayDecider("execution-id", WorkflowType(name="workflow-type"), worker)
    decider.next_decision_event_id = DECISION_EVENT_ID
    return decider


@pytest.fixture
def decision(decider):
    decision_id = DecisionId(DecisionTarget.TIMER, DECISION_EVENT_ID)
    decision = TimerDecisionStateMachine(decision_id, start_timer_attributes=StartTimerDecisionAttributes())
    decider.add_decision(decision_id, decision)
    return decision

@pytest.fixture
def mock_decision(decider):
    decision_id = DecisionId(DecisionTarget.TIMER, DECISION_EVENT_ID)
    decision = MagicMock()
    decider.add_decision(decision_id, decision)
    decision.is_done = Mock(return_value=True)
    return decision


@pytest.fixture
def mock_decision_context(decider: ReplayDecider):
    decision_context = MagicMock()
    decider.decision_context = decision_context
    return decision_context


def test_start_timer(decider):
    request = StartTimerDecisionAttributes()
    assert decider.start_timer(request) == DECISION_EVENT_ID
    decision_id = DecisionId(DecisionTarget.TIMER, DECISION_EVENT_ID)
    assert decision_id in decider.decisions
    state_machine = decider.decisions[decision_id]
    assert isinstance(state_machine, TimerDecisionStateMachine)
    assert state_machine.id == decision_id
    assert state_machine.start_timer_attributes == request


def test_cancel_timer_done(decider, decision):
    decision.state = DecisionState.COMPLETED
    assert decider.cancel_timer(DECISION_EVENT_ID, lambda: None) == True


def test_cancel_timer_not_done(decider, decision):
    invoked = False

    def callback():
        nonlocal invoked
        invoked = True

    assert decider.cancel_timer(DECISION_EVENT_ID, callback) == True
    assert invoked
    assert decider.next_decision_event_id == DECISION_EVENT_ID + 1


def test_handle_timer_closed(decider, mock_decision: DecisionStateMachine):
    attributes = TimerFiredEventAttributes()
    attributes.started_event_id = DECISION_EVENT_ID
    ret = decider.handle_timer_closed(attributes)
    assert ret is True
    mock_decision.handle_completion_event.assert_called_once()


def test_handle_timer_canceled(decider, mock_decision: DecisionStateMachine):
    event = HistoryEvent()
    event.timer_canceled_event_attributes = TimerCanceledEventAttributes()
    event.timer_canceled_event_attributes.started_event_id = DECISION_EVENT_ID
    ret = decider.handle_timer_canceled(event)
    assert ret is True
    mock_decision.handle_cancellation_event.assert_called_once()


def test_handle_cancel_timer_failed(decider, mock_decision: DecisionStateMachine):
    event = HistoryEvent()
    event.event_id = DECISION_EVENT_ID
    ret = decider.handle_cancel_timer_failed(event)
    assert ret is True
    mock_decision.handle_cancellation_failure_event.assert_called_once()
    args, kwargs = mock_decision.handle_cancellation_failure_event.call_args_list[0]
    assert args[0] is event


def test_handle_timer_started(decider, mock_decision: DecisionStateMachine):
    event = HistoryEvent()
    event.event_id = DECISION_EVENT_ID
    decider.handle_timer_started(event)
    mock_decision.handle_initiated_event.assert_called_once()
    args, kwargs = mock_decision.handle_initiated_event.call_args_list[0]
    assert args[0] is event


def test_handle_timer_fired(decider, mock_decision_context: DecisionContext):
    event = HistoryEvent()
    event.timer_fired_event_attributes = TimerFiredEventAttributes()
    decider.handle_timer_fired(event)
    mock_decision_context.handle_timer_fired.assert_called_once()
    args, kwargs = mock_decision_context.handle_timer_fired.call_args_list[0]
    assert args[0] is event.timer_fired_event_attributes


