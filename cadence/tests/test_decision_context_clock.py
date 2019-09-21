from unittest.mock import MagicMock, Mock

import pytest

from cadence.clock_decision_context import ClockDecisionContext
from cadence.decision_loop import DecisionContext

CREATE_TIMER_RETURN_VALUE = object()
CURRENT_TIME_MILLISECONDS = 1000


@pytest.fixture
def workflow_clock():
    workflow_clock = MagicMock()
    workflow_clock.create_timer = Mock(return_value=CREATE_TIMER_RETURN_VALUE)
    workflow_clock.current_time_millis = Mock(return_value=CURRENT_TIME_MILLISECONDS)
    return workflow_clock


@pytest.fixture
def decision_context(workflow_clock: ClockDecisionContext):
    decider = MagicMock()
    context = DecisionContext(decider, workflow_clock=workflow_clock)
    return context


def test_create_timer(decision_context, workflow_clock: ClockDecisionContext):
    def callback(ex):
        pass

    ret = decision_context.create_timer(555, callback)
    assert ret == CREATE_TIMER_RETURN_VALUE
    workflow_clock.create_timer.assert_called_once()
    args, kwargs = workflow_clock.create_timer.call_args_list[0]
    assert args[0] == 555
    assert args[1] == callback


def test_set_replay_current_time_milliseconds_before(decision_context, workflow_clock):
    with pytest.raises(Exception):
        decision_context.set_replay_current_time_milliseconds(CURRENT_TIME_MILLISECONDS - 1)


def test_set_replay_current_time_milliseconds(decision_context, workflow_clock: ClockDecisionContext):
    decision_context.set_replay_current_time_milliseconds(CURRENT_TIME_MILLISECONDS + 10)
    workflow_clock.set_replay_current_time_milliseconds.assert_called_once()
    args, kwargs = workflow_clock.set_replay_current_time_milliseconds.call_args_list[0]
    assert args[0] == CURRENT_TIME_MILLISECONDS + 10


def test_current_time_millis(decision_context: DecisionContext):
    assert decision_context.current_time_millis() == CURRENT_TIME_MILLISECONDS


def test_set_replaying(decision_context: DecisionContext, workflow_clock: ClockDecisionContext):
    decision_context.set_replaying(False)
    workflow_clock.set_replaying.assert_called_once()
    args, kwargs = workflow_clock.set_replaying.call_args_list[0]
    assert args[0] is False


def test_is_replaying(decision_context, workflow_clock):
    workflow_clock.is_replaying = Mock(return_value=False)
    assert decision_context.is_replaying() is False
    workflow_clock.is_replaying.assert_called_once()

