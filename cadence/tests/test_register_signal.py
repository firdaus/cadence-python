import pytest

from cadence.worker import Worker
from cadence.workflow import signal_method


class TestWorkflow:

    @signal_method()
    def the_signal_method(self):
        pass


@pytest.fixture
def worker():
    return Worker()


def test_register_init_signal_methods(worker):
    worker.register_workflow_implementation_type(TestWorkflow)
    assert TestWorkflow._signal_methods


def test_register_mappings(worker):
    worker.register_workflow_implementation_type(TestWorkflow)
    assert TestWorkflow._signal_methods["TestWorkflow::the_signal_method"] == TestWorkflow.the_signal_method


def test_camel_case(worker):
    worker.register_workflow_implementation_type(TestWorkflow)
    assert TestWorkflow._signal_methods["TestWorkflow::theSignalMethod"] == TestWorkflow.the_signal_method


def test_custom_mapping(worker):
    class CustomNameWorkflow:
        @signal_method(name="blah")
        def the_signal_method(self):
            pass

    worker.register_workflow_implementation_type(CustomNameWorkflow)
    assert CustomNameWorkflow._signal_methods["blah"] == CustomNameWorkflow.the_signal_method
