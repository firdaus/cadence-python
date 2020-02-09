import pytest

from cadence.decision_loop import DecisionEvents


@pytest.fixture()
def event_object():
    return object()


@pytest.fixture()
def decision_events(event_object):
    events = DecisionEvents(events=[],
                            decision_events=[event_object],
                            replay=False,
                            replay_current_time_milliseconds=0,
                            next_decision_event_id=20)
    return events


def test_get_optional_decision_event(decision_events, event_object):
    e = decision_events.get_optional_decision_event(20)
    assert e is event_object


def test_get_optional_event_negative(decision_events):
    e = decision_events.get_optional_decision_event(10)
    assert e is None


def test_get_optional_event_too_large(decision_events):
    e = decision_events.get_optional_decision_event(25)
    assert e is None
