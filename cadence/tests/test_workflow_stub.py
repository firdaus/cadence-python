import json
from unittest.mock import Mock, MagicMock

import pytest

from cadence.cadence_types import WorkflowExecution, SignalWorkflowExecutionRequest
from cadence.workflow import WorkflowClient, signal_method, WorkflowStub, SignalMethod
from cadence.workflowservice import WorkflowService


@pytest.fixture
def workflow_service():
    m = Mock(spec=WorkflowService)
    m.signal_workflow_execution = MagicMock(return_value=(object(), None))
    return m


@pytest.fixture
def workflow_client(workflow_service):
    return WorkflowClient(service=workflow_service, domain="domain", options=None)


@pytest.fixture
def workflow_execution():
    return WorkflowExecution(workflow_id="the-workflow-id", run_id="the-run-id")


class DummyWorkflow:
    @signal_method()
    def the_signal_method(self, name, age):
        pass


def test_new_workflow_stub_signal(workflow_client):
    stub = workflow_client.new_workflow_stub(DummyWorkflow)
    assert isinstance(stub, WorkflowStub)
    assert hasattr(stub, "the_signal_method")
    assert hasattr(stub.the_signal_method, "_signal_method")
    assert isinstance(stub.the_signal_method._signal_method, SignalMethod)


def test_exec_signal(workflow_client, workflow_service, workflow_execution):
    stub = workflow_client.new_workflow_stub(DummyWorkflow)
    stub._execution = workflow_execution
    stub.the_signal_method("bob", 25)
    workflow_service.signal_workflow_execution.assert_called_once()
    args, kwargs = workflow_service.signal_workflow_execution.call_args_list[0]
    request: SignalWorkflowExecutionRequest = args[0]
    assert request.signal_name == "DummyWorkflow::the_signal_method"
    assert request.input == json.dumps(["bob", 25])
    assert request.workflow_execution == workflow_execution
