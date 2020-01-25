import json

from cadence.exception_handling import serialize_exception, deserialize_exception, THIS_SOURCE


class TestException(Exception):
    pass


def test_serialize_deserialize_exception():
    try:
        raise TestException("here")
    except Exception as e:
        ex = e

    reason, details = serialize_exception(ex)
    assert reason == "cadence.tests.test_exception_handling.TestException"
    details_dict = json.loads(details)
    assert details_dict["repr"] == "TestException('here')"
    assert details_dict["source"] == THIS_SOURCE
    assert details_dict["traceback"]

    dex = deserialize_exception(reason, details)
    assert type(dex) == TestException
    assert repr(dex) == repr(ex)
    assert dex.__traceback__
