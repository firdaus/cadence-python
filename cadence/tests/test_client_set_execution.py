from unittest.mock import MagicMock, Mock

import pytest

from cadence.cadence_types import StartWorkflowExecutionResponse
from cadence.workflow import WorkflowClient, workflow_method
from cadence.workflowservice import WorkflowService


class DummyWorkflow:
    @workflow_method()
    def dummy_workflow(self):
        pass


@pytest.fixture
def workflow_service():
    m = Mock(spec=WorkflowService)
    start_response = StartWorkflowExecutionResponse(run_id="the-run-id")
    m.start_workflow = Mock()
    m.start_workflow.return_value = start_response, None
    return m


@pytest.fixture
def workflow_client(workflow_service):
    client = WorkflowClient(service=workflow_service,
                          domain="dummy",
                          options=None)
    client.wait_for_close = Mock()
    return client


@pytest.fixture
def workflow_stub(workflow_client):
    return workflow_client.new_workflow_stub(DummyWorkflow)


def test_set_execution_async(workflow_client: WorkflowClient, workflow_stub: DummyWorkflow):
    workflow_client.start(workflow_stub.dummy_workflow)
    assert workflow_stub._execution
    assert workflow_stub._execution.run_id == "the-run-id"


def test_set_execution_sync(workflow_client: WorkflowClient, workflow_stub: DummyWorkflow):
    workflow_stub.dummy_workflow()
    assert workflow_stub._execution
    assert workflow_stub._execution.run_id == "the-run-id"
