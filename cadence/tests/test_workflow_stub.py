from unittest.mock import Mock

import pytest

from cadence.workflow import WorkflowClient, signal_method, WorkflowStub, SignalMethod


@pytest.fixture
def workflow_service():
    return Mock()


@pytest.fixture
def workflow_client(workflow_service):
    return WorkflowClient(service=workflow_service, domain="domain", options=None)


class DummyWorkflow:
    @signal_method()
    def the_signal_method(self):
        pass


def test_new_workflow_stub_signal(workflow_client):
    stub = workflow_client.new_workflow_stub(DummyWorkflow)
    assert isinstance(stub, WorkflowStub)
    assert hasattr(stub, "the_signal_method")
    assert hasattr(stub.the_signal_method, "_signal_method")
    assert isinstance(stub.the_signal_method._signal_method, SignalMethod)
