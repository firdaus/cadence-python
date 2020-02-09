import json
from unittest.mock import MagicMock, Mock

import pytest

from cadence.cadence_types import WorkflowType, DecisionType, MarkerRecordedEventAttributes, Header, HistoryEvent, \
    EventType
from cadence.decision_loop import ReplayDecider, DecisionContext, DecisionEvents
from cadence.decisions import DecisionId, DecisionTarget
from cadence.marker import MarkerData, MUTABLE_MARKER_HEADER_KEY, MarkerHandler, MarkerInterface, PlainMarkerData, \
    MarkerHeader, MarkerResult
from cadence.state_machines import MarkerDecisionStateMachine

DECISION_EVENT_ID = 55


@pytest.fixture
def decider():
    worker = MagicMock()
    decider = ReplayDecider("execution-id", WorkflowType(name="workflow-type"), worker)
    decider.next_decision_event_id = DECISION_EVENT_ID
    return decider


@pytest.fixture
def header():
    marker_data = MarkerData.create("id", 10, "abc".encode("utf-8"), 9)
    header = marker_data.get_header()
    return header


def test_marker_data_create():
    marker_data = MarkerData.create("id", 10, "abc".encode("utf-8"), 9)
    assert marker_data.header.id == "id"
    assert marker_data.header.event_id == 10
    assert marker_data.header.access_count == 9
    assert marker_data.data == "abc".encode("utf-8")


def test_marker_data_get_header(header):
    assert MUTABLE_MARKER_HEADER_KEY in header.fields
    json.loads(header.fields[MUTABLE_MARKER_HEADER_KEY])


def test_marker_handler_record_mutable_marker():
    decision_context = MagicMock()
    handler = MarkerHandler(decision_context=decision_context, marker_name="test")
    handler.record_mutable_marker("theid", 20, "thedata".encode("utf-8"), 0)
    assert "theid" in handler.mutable_marker_results
    decision_context.record_marker.assert_called_once()


def test_record_marker(decider, header):
    decision_context = DecisionContext(decider=decider)
    decision_context.record_marker("marker-name", header, bytes())
    assert len(decider.decisions) == 1
    decision_id: DecisionId
    state_machine: MarkerDecisionStateMachine
    decision_id, state_machine = list(decider.decisions.items())[0]
    assert decision_id.decision_event_id == DECISION_EVENT_ID
    assert decision_id.decision_target == DecisionTarget.MARKER
    assert state_machine.decision.decision_type == DecisionType.RecordMarker
    attr = state_machine.decision.record_marker_decision_attributes
    assert attr.marker_name == "marker-name"
    assert attr.header == header
    assert attr.details == bytes()


def test_marker_data_from_event_attributes():
    attr = MarkerRecordedEventAttributes()
    attr.header = Header()
    attr.header.fields[MUTABLE_MARKER_HEADER_KEY] = '{"id": "test-id"}'.encode("utf-8")
    attr.details = b'blah'
    marker_data = MarkerInterface.from_event_attributes(attr)
    assert isinstance(marker_data, MarkerData)
    assert marker_data.header.id == "test-id"
    assert marker_data.data == attr.details


def test_plain_marker_data_from_event_attributes():
    attr = MarkerRecordedEventAttributes()
    attr.details = '{"id": "test-id"}'.encode("utf-8")
    marker_data = MarkerInterface.from_event_attributes(attr)
    assert isinstance(marker_data, PlainMarkerData)
    assert marker_data.id == "test-id"


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
    decision_context.decider.decision_events = DecisionEvents(events=[],
                                                              decision_events=[marker_recorded_event],
                                                              replay=False,
                                                              replay_current_time_milliseconds=0,
                                                              next_decision_event_id=20)
    decision_context.decider.next_decision_event_id = 20
    return decision_context


def test_get_marker_data_from_history(marker_recorded_event, decision_context):
    handler = MarkerHandler(decision_context=decision_context, marker_name="the-marker-name")
    data = handler.get_marker_data_from_history(event_id=20, marker_id="the-id", expected_access_count=35)
    assert data == b'blah-blah'


def test_get_marker_data_from_history_wrong_event_type(marker_recorded_event, decision_context):
    decision_context.decider.decision_events.decision_events[0].event_type = EventType.ActivityTaskCompleted
    handler = MarkerHandler(decision_context=decision_context, marker_name="the-marker-name")
    data = handler.get_marker_data_from_history(event_id=20, marker_id="the-id", expected_access_count=35)
    assert data is None


def test_get_marker_data_wrong_name(marker_recorded_event, decision_context):
    handler = MarkerHandler(decision_context=decision_context, marker_name="the-marker-name-different-one")
    data = handler.get_marker_data_from_history(event_id=20, marker_id="the-id", expected_access_count=35)
    assert data is None


def test_get_marker_data_lower_access_count(marker_recorded_event, decision_context):
    handler = MarkerHandler(decision_context=decision_context, marker_name="the-marker-name")
    data = handler.get_marker_data_from_history(event_id=20, marker_id="the-id", expected_access_count=9)
    assert data is None


def test_handle_replaying_get_from_history(decision_context):
    def callback(stored):
        raise Exception("Should not be executed")

    handler = MarkerHandler(decision_context=decision_context, marker_name="the-marker-name")
    handler.mutable_marker_results["the-id"] = MarkerResult(data=b'123', access_count=35)
    ret = handler.handle("the-id", callback)
    assert ret == b'blah-blah'
    assert len(decision_context.decider.decisions) == 1


def test_handle_replaying_no_history(decision_context):
    def callback(stored):
        raise Exception("Should not be executed")

    decision_context.decider.next_decision_event_id = 25
    handler = MarkerHandler(decision_context=decision_context, marker_name="the-marker-name")
    handler.mutable_marker_results["the-id"] = MarkerResult(data=b'123', access_count=35)
    ret = handler.handle("the-id", callback)
    assert ret == b'123'
    assert len(decision_context.decider.decisions) == 0


def test_handle_not_replaying_callback_returns_not_none(decision_context):
    def callback(stored):
        return b'456'

    decision_context.workflow_clock.set_replaying(False)
    handler = MarkerHandler(decision_context=decision_context, marker_name="the-marker-name")
    handler.mutable_marker_results["the-id"] = MarkerResult(data=b'123', access_count=35)
    ret = handler.handle("the-id", callback)
    assert ret == b'456'
    assert len(decision_context.decider.decisions) == 1


def test_handle_not_replaying_callback_returns_none(decision_context):
    def callback(stored):
        return None

    decision_context.workflow_clock.set_replaying(False)
    handler = MarkerHandler(decision_context=decision_context, marker_name="the-marker-name")
    handler.mutable_marker_results["the-id"] = MarkerResult(data=b'123', access_count=35)
    ret = handler.handle("the-id", callback)
    assert ret == b'123'
    assert len(decision_context.decider.decisions) == 0
