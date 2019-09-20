from unittest.mock import MagicMock

import pytest

from cadence.cadence_types import WorkflowType, StartTimerDecisionAttributes
from cadence.decision_loop import ReplayDecider
from cadence.decisions import DecisionId, DecisionTarget, DecisionState
from cadence.state_machines import TimerDecisionStateMachine

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
