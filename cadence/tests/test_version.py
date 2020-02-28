import pytest
from unittest.mock import Mock

from cadence.cadence_types import HistoryEvent, EventType, MarkerRecordedEventAttributes, Header
from cadence.clock_decision_context import VERSION_MARKER_NAME
from cadence.decision_loop import ReplayDecider, DecisionContext, DecisionEvents
from cadence.marker import MarkerResult, MarkerHeader, MUTABLE_MARKER_HEADER_KEY


@pytest.fixture()
def marker_header_json():
    marker_header = MarkerHeader(id="the-id", event_id=55, access_count=35)
    return marker_header.to_json()


@pytest.fixture()
def marker_recorded_event(marker_header_json):
    event = HistoryEvent()
    event.event_id = 20
    event.event_type = EventType.MarkerRecorded
    event.marker_recorded_event_attributes = MarkerRecordedEventAttributes()
    event.marker_recorded_event_attributes.marker_name = "the-marker-name"
    event.marker_recorded_event_attributes.header = Header()
    event.marker_recorded_event_attributes.header.fields[MUTABLE_MARKER_HEADER_KEY] = bytes(marker_header_json, "utf-8")
    event.marker_recorded_event_attributes.details = b'blah-blah'
    return event


@pytest.fixture()
def decision_context(marker_recorded_event):
    decider = ReplayDecider(execution_id=Mock(), workflow_type=Mock(), worker=Mock())
    decision_context = DecisionContext(decider=decider)
    decider.decision_context = decision_context
    decider.decision_context.workflow_clock.version_handler.decision_context = decision_context
    decision_context.decider.decision_events = DecisionEvents(events=[],
                                                              decision_events=[marker_recorded_event],
                                                              replay=False,
                                                              replay_current_time_milliseconds=0,
                                                              next_decision_event_id=20)
    decision_context.decider.next_decision_event_id = 20
    return decision_context


def test_clock_decision_context_get_version(decision_context):
    decision_context.workflow_clock.set_replaying(False)
    assert len(decision_context.decider.decisions) == 0
    version = decision_context.workflow_clock.get_version("abc", 1, 5)
    assert version == 5
    assert len(decision_context.decider.decisions) == 1


def test_clock_decision_context_get_version_stored(decision_context):
    decision_context.workflow_clock.version_handler.mutable_marker_results["abc"] = MarkerResult(data="3")
    version = decision_context.workflow_clock.get_version("abc", 1, 5)
    assert version == 3
    assert len(decision_context.decider.decisions) == 0


@pytest.fixture()
def version_marker_recorded_event(marker_header_json):
    marker_header_json = MarkerHeader(id="abc", event_id=55, access_count=0).to_json()
    event = HistoryEvent()
    event.event_id = 20
    event.event_type = EventType.MarkerRecorded
    event.marker_recorded_event_attributes = MarkerRecordedEventAttributes()
    event.marker_recorded_event_attributes.marker_name = VERSION_MARKER_NAME
    event.marker_recorded_event_attributes.header = Header()
    event.marker_recorded_event_attributes.header.fields[MUTABLE_MARKER_HEADER_KEY] = bytes(marker_header_json, "utf-8")
    event.marker_recorded_event_attributes.details = b'4'
    return event


@pytest.fixture()
def version_decision_context(version_marker_recorded_event):
    decider = ReplayDecider(execution_id=Mock(), workflow_type=Mock(), worker=Mock())
    decision_context = DecisionContext(decider=decider)
    decider.decision_context = decision_context
    decider.decision_context.workflow_clock.version_handler.decision_context = decision_context
    decision_context.decider.decision_events = DecisionEvents(events=[],
                                                              decision_events=[version_marker_recorded_event],
                                                              replay=True,
                                                              replay_current_time_milliseconds=0,
                                                              next_decision_event_id=20)
    decision_context.decider.next_decision_event_id = 20
    return decision_context


def test_clock_decision_context_from_replay(version_decision_context):
    version_decision_context.workflow_clock.set_replaying(True)
    version = version_decision_context.workflow_clock.get_version("abc", 1, 5)
    assert version == -1
    assert len(version_decision_context.decider.decisions) == 0


def test_validate_version(version_decision_context):
    with pytest.raises(Exception):
        version_decision_context.workflow_clock.validate_version("abc", 5, 1, 3)

    with pytest.raises(Exception):
        version_decision_context.workflow_clock.validate_version("abc", 1, 2, 3)

    version_decision_context.workflow_clock.validate_version("abc", 2, 2, 3)
    version_decision_context.workflow_clock.validate_version("abc", 3, 2, 3)
