from unittest.mock import MagicMock, ANY

import pytest

from cadence.clock_decision_context import TimerCancellationHandler


@pytest.fixture
def clock_decision_context():
    clock_decision_context = MagicMock()
    clock_decision_context.decider = MagicMock()
    return clock_decision_context


@pytest.fixture
def handler(clock_decision_context):
    handler = TimerCancellationHandler(start_event_id=20,
                                       clock_decision_context=clock_decision_context)
    return handler


def test_cancel_timer(clock_decision_context, handler):
    reason = Exception()
    handler.accept(reason)
    clock_decision_context.decider.cancel_timer.assert_called_once_with(20, ANY)


def test_timer_cancelled(clock_decision_context, handler):
    reason = Exception()
    handler.accept(reason)
    args, kwargs = clock_decision_context.decider.cancel_timer.call_args_list[0]
    callback = args[1]
    callback()
    clock_decision_context.timer_cancelled.assert_called_once_with(20, reason)
