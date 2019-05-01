from unittest import TestCase
from uuid import uuid4

from cadence.errors import WorkflowExecutionAlreadyStartedError, DomainAlreadyExistsError
from cadence.types import StartWorkflowExecutionRequest, TaskList, WorkflowType, StartWorkflowExecutionResponse
from cadence.workflowservice import WorkflowService


class TestStartWorkflow(TestCase):

    def setUp(self) -> None:
        self.service = WorkflowService.create("localhost", 7933)

    def test_start_workflow(self):
        request = StartWorkflowExecutionRequest()
        request.domain = "test-domain"
        request.request_id = str(uuid4())
        request.task_list = TaskList()
        request.task_list.name = "test-task-list"
        request.input = "abc-firdaus"
        request.workflow_id = str(uuid4())
        request.workflow_type = WorkflowType()
        request.workflow_type.name = "firdaus-workflow-type"
        request.execution_start_to_close_timeout_seconds = 86400
        request.task_start_to_close_timeout_seconds = 120

        (response, err) = self.service.start_workflow(request)

        self.assertIsNotNone(response)
        self.assertIsInstance(response, StartWorkflowExecutionResponse)

    def test_duplicate_workflow_ids(self):
        workflow_id = str(uuid4())
        (runId, err) = self.service.start_workflow("test-domain", "test-tasklist", "firdaus-workflow-type",
                                                   input_value="abc-firdaus", workflow_id=workflow_id)
        (runId, err) = self.service.start_workflow("test-domain", "test-tasklist", "firdaus-workflow-type",
                                                   input_value="abc-firdaus", workflow_id=workflow_id)
        self.assertIsNotNone(err)
        self.assertIsNone(runId)
        self.assertIsInstance(err, WorkflowExecutionAlreadyStartedError)

    def test_register_domain(self):
        domain = str(uuid4())
        response, err = self.service.register_domain(domain)
        self.assertIsNone(response)  # RegisterDomain returns void
        self.assertIsNone(err)

    def test_duplicate_domains(self):
        domain = str(uuid4())
        response, err = self.service.register_domain(domain)
        response, err = self.service.register_domain(domain)
        self.assertIsNotNone(err)
        self.assertIsInstance(err, DomainAlreadyExistsError)

    def test_poll_for_activity_task(self):
        # response, err = self.service.poll_for_activity_task("test-domain", "test-tasklist")
        # self.assertIsNotNone(response)
        pass

    def tearDown(self) -> None:
        self.service.connection.close()
