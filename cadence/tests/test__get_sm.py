from unittest import TestCase

from cadence.worker import _get_sm
from cadence.workflow import signal_method


class TestWorkflow:
    @signal_method()
    def signal_test(self):
        pass


def test__get_sm():
    sm = _get_sm(TestWorkflow, "signal_test")
    assert sm
    assert sm.name == "TestWorkflow::signal_test"
