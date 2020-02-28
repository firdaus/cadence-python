import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, Any, Union

import json

from cadence.cadence_types import StartTimerDecisionAttributes, TimerFiredEventAttributes, HistoryEvent, \
    TimerCanceledEventAttributes
from cadence.conversions import args_to_json
from cadence.decision_loop import ReplayDecider, DecisionContext
from cadence.exceptions import CancellationException
from cadence.marker import MarkerHandler, MarkerInterface, MarkerResult
from cadence.util import OpenRequestInfo

logger = logging.getLogger(__name__)

SIDE_EFFECT_MARKER_NAME = "SideEffect"
MUTABLE_SIDE_EFFECT_MARKER_NAME = "MutableSideEffect"
VERSION_MARKER_NAME = "Version"
LOCAL_ACTIVITY_MARKER_NAME = "LocalActivity"


DEFAULT_VERSION = -1

@dataclass
class ClockDecisionContext:
    decider: ReplayDecider
    decision_context: DecisionContext
    scheduled_timers: Dict[int, OpenRequestInfo] = field(default_factory=dict)
    replay_current_time_milliseconds: int = -1
    replaying: bool = True
    version_handler: MarkerHandler = None

    def __post_init__(self):
        self.version_handler = MarkerHandler(self.decision_context, VERSION_MARKER_NAME)

    def set_replay_current_time_milliseconds(self, s):
        self.replay_current_time_milliseconds = s

    def current_time_millis(self):
        return self.replay_current_time_milliseconds

    def create_timer(self, delay_seconds: int, callback: Callable):
        if delay_seconds < 0:
            raise Exception("Negative delay seconds: " + str(delay_seconds))
        if delay_seconds == 0:
            callback(None)
            return None
        firing_time = self.current_time_millis() + delay_seconds * 1000
        context = OpenRequestInfo(user_context=firing_time)
        timer = StartTimerDecisionAttributes()
        timer.start_to_fire_timeout_seconds = delay_seconds
        timer.timer_id = str(self.decider.get_and_increment_next_id())
        start_event_id: int = self.decider.start_timer(timer)
        context.completion_handle = lambda ctx, e: callback(e)
        self.scheduled_timers[start_event_id] = context
        return TimerCancellationHandler(start_event_id=start_event_id, clock_decision_context=self)

    def is_replaying(self):
        return self.replaying

    def set_replaying(self, replaying):
        self.replaying = replaying

    def timer_cancelled(self, start_event_id: int, reason: Exception):
        scheduled: OpenRequestInfo = self.scheduled_timers.pop(start_event_id, None)
        if not scheduled:
            return
        callback = scheduled.completion_handle
        exception = CancellationException("Cancelled by request")
        exception.init_cause(reason)
        callback(None, exception)

    def handle_timer_fired(self, attributes: TimerFiredEventAttributes):
        started_event_id: int = attributes.started_event_id
        if self.decider.handle_timer_closed(attributes):
            scheduled = self.scheduled_timers.pop(started_event_id, None)
            if scheduled:
                callback = scheduled.completion_handle
                callback(None, None)

    def handle_timer_canceled(self, event: HistoryEvent):
        attributes: TimerCanceledEventAttributes = event.timer_canceled_event_attributes
        started_event_id: int = attributes.started_event_id
        if self.decider.handle_timer_canceled(event):
            self.timer_cancelled(started_event_id, None)

    def get_version(self, change_id: str, min_supported: int, max_supported) -> int:
        def func():
            return json.dumps(max_supported)

        result: bytes = self.version_handler.handle(change_id, func)
        if result is None:
            result = json.dumps(DEFAULT_VERSION)
            self.version_handler.set_data(change_id, result)
            self.version_handler.mark_replayed(change_id)  # so that we don't ever emit a MarkerRecorded for this

        version: int = json.loads(result)
        self.validate_version(change_id, version, min_supported, max_supported)
        return version

    def validate_version(self, change_id: str, version: int, min_supported: int, max_supported: int):
        if version < min_supported or version > max_supported:
            raise Exception(f"Version {version} of changeID {change_id} is not supported. "
                            f"Supported version is between {min_supported} and {max_supported}.")

    def handle_marker_recorded(self, event: HistoryEvent):
        """
        Will be executed more than once for the same event.
        """
        attributes = event.marker_recorded_event_attributes
        name: str = attributes.marker_name
        if SIDE_EFFECT_MARKER_NAME == name:
            # TODO
            # sideEffectResults.put(event.getEventId(), attributes.getDetails());
            pass
        elif LOCAL_ACTIVITY_MARKER_NAME == name:
            # TODO
            # handleLocalActivityMarker(attributes);
            pass
        elif VERSION_MARKER_NAME == name:
            marker_data = MarkerInterface.from_event_attributes(attributes)
            change_id: str = marker_data.get_id()
            data: bytes = marker_data.get_data()
            self.version_handler.mutable_marker_results[change_id] = MarkerResult(data=data)
        elif MUTABLE_SIDE_EFFECT_MARKER_NAME != name:
            # TODO
            # if (log.isWarnEnabled()) {
            #       log.warn("Unexpected marker: " + event);
            # }
            pass



@dataclass
class TimerCancellationHandler:
    start_event_id: int
    clock_decision_context: ClockDecisionContext

    def accept(self, reason: Exception):
        self.clock_decision_context.decider.cancel_timer(self.start_event_id,
                                                         lambda: self.clock_decision_context.timer_cancelled(
                                                             self.start_event_id, reason))
