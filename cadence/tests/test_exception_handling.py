import json
import traceback

import tblib

from cadence.exception_handling import serialize_exception, deserialize_exception, THIS_SOURCE, ExternalException


class TestException(Exception):
    pass


def a():
    b()


def b():
    c()


def c():
    d()


def d():
    raise TestException("here")


def test_serialize_deserialize_exception():
    try:
        a()
    except TestException as e:
        ex = e

    details = serialize_exception(ex)
    details_dict = json.loads(details)
    assert details_dict["class"] == "cadence.tests.test_exception_handling.TestException"
    assert details_dict["args"] == ["here"]
    assert details_dict["traceback"]
    assert details_dict["source"] == "cadence-python"

    dex = deserialize_exception(details)
    assert type(dex) == TestException
    assert repr(dex) == repr(ex)
    assert dex.__traceback__


def test_deserialize_unknown_exception():
    details_dict = {
        "class": "java.lang.Exception"
    }
    details = json.dumps(details_dict)
    exception = deserialize_exception(details)
    assert isinstance(exception, ExternalException)
    assert exception.details == details_dict
