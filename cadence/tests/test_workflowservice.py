from unittest import TestCase
from uuid import uuid4

from cadence.errors import WorkflowExecutionAlreadyStartedError
from cadence.workflowservice import WorkflowService


class TestStartWorkflow(TestCase):

    def setUp(self) -> None:
        self.service = WorkflowService.create("localhost", 7933)

    def test_start_workflow(self):
        (runId, err) = self.service.start_workflow("test-domain", "test-tasklist", "firdaus-workflow-type",
                                                   input_value="abc-firdaus")
        self.assertIsNotNone(runId)
        self.assertIsInstance(runId, str)

    def test_duplicate_workflow_ids(self):
        workflow_id = str(uuid4())
        (runId, err) = self.service.start_workflow("test-domain", "test-tasklist", "firdaus-workflow-type",
                                                   input_value="abc-firdaus", workflow_id=workflow_id)
        (runId, err) = self.service.start_workflow("test-domain", "test-tasklist", "firdaus-workflow-type",
                                                   input_value="abc-firdaus", workflow_id=workflow_id)
        self.assertIsNotNone(err)
        self.assertIsNone(runId)
        self.assertIsInstance(err, WorkflowExecutionAlreadyStartedError)

    def tearDown(self) -> None:
        self.service.connection.close()
