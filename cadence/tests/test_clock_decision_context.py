from typing import Callable
from unittest.mock import MagicMock, Mock

import pytest

from cadence.cadence_types import StartTimerDecisionAttributes, TimerFiredEventAttributes, HistoryEvent, \
    TimerCanceledEventAttributes
from cadence.clock_decision_context import ClockDecisionContext, TimerCancellationHandler
from cadence.exceptions import CancellationException
from cadence.util import OpenRequestInfo

TIMER_ID = 20
START_TIMER_ID = 25
REPLAY_CURRENT_TIME_MS = 1000


@pytest.fixture
def decider():
    mock = MagicMock()
    mock.get_and_increment_next_id = Mock(return_value=TIMER_ID)
    mock.start_timer = Mock(return_value=START_TIMER_ID)
    mock.handle_timer_closed = Mock(return_value=True)
    mock.handle_timer_canceled = Mock(return_value=True)
    return mock


@pytest.fixture
def clock_decision_context(decider):
    context = ClockDecisionContext(decider=decider)
    context.set_replay_current_time_milliseconds(REPLAY_CURRENT_TIME_MS)
    return context

@pytest.fixture
def request_info(clock_decision_context):
    info = OpenRequestInfo(user_context=999)
    info.completion_handle = Mock()
    clock_decision_context.scheduled_timers[START_TIMER_ID] = info
    return info


def test_negative(clock_decision_context):
    with pytest.raises(Exception):
        clock_decision_context.create_timer(-1, lambda *args: None)


def test_zero_delay(clock_decision_context):
    invoked = False
    arg = object()

    def callback(exception):
        nonlocal invoked, arg
        invoked = True
        arg = exception

    clock_decision_context.create_timer(0, callback)
    assert invoked
    assert arg is None


def test_context_creation(clock_decision_context):
    clock_decision_context.create_timer(60, lambda *args: None)
    assert START_TIMER_ID in clock_decision_context.scheduled_timers
    open_request: OpenRequestInfo = clock_decision_context.scheduled_timers[START_TIMER_ID]
    assert isinstance(open_request, OpenRequestInfo)
    assert open_request.completion_handle
    assert isinstance(open_request.completion_handle, Callable)


def test_firing_time(clock_decision_context):
    clock_decision_context.create_timer(60, lambda *args: None)
    open_request = clock_decision_context.scheduled_timers[START_TIMER_ID]
    assert open_request.user_context == REPLAY_CURRENT_TIME_MS + 60 * 1000


def test_completion_handle(clock_decision_context):
    exception = None
    invoked = False

    def callback(e):
        nonlocal invoked, exception
        exception = e
        invoked = True

    clock_decision_context.create_timer(60, callback)
    open_request = clock_decision_context.scheduled_timers[START_TIMER_ID]
    arg_exception = Exception()
    open_request.completion_handle(object(), arg_exception)
    assert invoked
    assert exception is arg_exception


def test_start_timer(clock_decision_context, decider):
    clock_decision_context.create_timer(60, lambda *a: None)
    decider.start_timer.assert_called_once()
    args, kwargs = decider.start_timer.call_args_list[0]
    timer: StartTimerDecisionAttributes = args[0]
    assert timer.timer_id == str(TIMER_ID)
    assert timer.start_to_fire_timeout_seconds == 60


def test_return_value(clock_decision_context):
    handler = clock_decision_context.create_timer(60, lambda *args: None)
    assert isinstance(handler, TimerCancellationHandler)
    assert handler.clock_decision_context is clock_decision_context
    assert handler.start_event_id == START_TIMER_ID


def test_cancelled_invalid_start_event_id(clock_decision_context, request_info):
    clock_decision_context.timer_cancelled(1111, Exception())
    request_info.completion_handle.assert_not_called()


def test_cancelled(clock_decision_context, request_info):
    exception = Exception()
    clock_decision_context.timer_cancelled(START_TIMER_ID, exception)
    request_info.completion_handle.assert_called_once()
    args, kwargs = request_info.completion_handle.call_args_list[0]
    assert args[0] is None
    assert isinstance(args[1], CancellationException)
    assert args[1].cause is exception


def test_handle_timer_fired(clock_decision_context: ClockDecisionContext, request_info, decider):
    attributes = TimerFiredEventAttributes()
    attributes.started_event_id = START_TIMER_ID
    clock_decision_context.handle_timer_fired(attributes)
    decider.handle_timer_closed.assert_called_once()
    args, kwargs = decider.handle_timer_closed.call_args_list[0]
    assert args[0] is attributes
    assert len(clock_decision_context.scheduled_timers) == 0
    request_info.completion_handle.assert_called_once()
    args, kwargs = request_info.completion_handle.call_args_list[0]
    assert args[0] is None
    assert args[1] is None


def test_handle_timer_canceled(clock_decision_context, decider, request_info):
    event = HistoryEvent()
    event.timer_canceled_event_attributes = TimerCanceledEventAttributes()
    event.timer_canceled_event_attributes.started_event_id = START_TIMER_ID
    clock_decision_context.handle_timer_canceled(event)
    assert len(clock_decision_context.scheduled_timers) == 0
    decider.handle_timer_canceled.assert_called_once()
    request_info.completion_handle.assert_called_once()
    args, kwargs = request_info.completion_handle.call_args_list[0]
    assert args[0] is None
    assert isinstance(args[1], Exception)

