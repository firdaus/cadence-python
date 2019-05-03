from unittest import TestCase
from unittest.mock import create_autospec
from uuid import uuid4
import time
import calendar

from cadence.errors import WorkflowExecutionAlreadyStartedError, DomainAlreadyExistsError, EntityNotExistsError
from cadence.tchannel import TChannelException
from cadence.types import StartWorkflowExecutionRequest, TaskList, WorkflowType, StartWorkflowExecutionResponse, \
    RegisterDomainRequest, PollForActivityTaskRequest, DescribeTaskListRequest, TaskListType, \
    DescribeWorkflowExecutionRequest, WorkflowExecution, DescribeTaskListResponse, DescribeWorkflowExecutionResponse, \
    QueryWorkflowRequest, WorkflowQuery, ResetStickyTaskListRequest, RespondQueryTaskCompletedRequest, \
    QueryTaskCompletedType, ListClosedWorkflowExecutionsRequest, ListClosedWorkflowExecutionsResponse, StartTimeFilter, \
    ListOpenWorkflowExecutionsRequest, TerminateWorkflowExecutionRequest, SignalWithStartWorkflowExecutionRequest, \
    SignalWorkflowExecutionRequest, RequestCancelWorkflowExecutionRequest, RespondActivityTaskCanceledByIDRequest, \
    RespondActivityTaskCanceledRequest, RespondActivityTaskFailedByIDRequest, RespondActivityTaskFailedRequest, \
    RespondActivityTaskCompletedByIDRequest, RecordActivityTaskHeartbeatByIDRequest, RecordActivityTaskHeartbeatRequest, \
    RespondDecisionTaskFailedRequest, DecisionTaskFailedCause, RespondDecisionTaskCompletedRequest, \
    PollForDecisionTaskRequest, GetWorkflowExecutionHistoryRequest
from cadence.workflowservice import WorkflowService


class TestStartWorkflow(TestCase):

    def setUp(self) -> None:
        self.service = WorkflowService.create("localhost", 7933)

        self.request = request = StartWorkflowExecutionRequest()
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

    def test_start_workflow(self):
        (response, err) = self.service.start_workflow(self.request)

        self.assertIsNotNone(response)
        self.assertIsInstance(response, StartWorkflowExecutionResponse)

    def test_duplicate_workflow_ids(self):
        (response, err) = self.service.start_workflow(self.request)
        self.request.request_id = str(uuid4())
        (response, err) = self.service.start_workflow(self.request)
        self.assertIsNotNone(err)
        self.assertIsNone(response)
        self.assertIsInstance(err, WorkflowExecutionAlreadyStartedError)

    def test_register_domain(self):
        request = RegisterDomainRequest()
        request.name = str(uuid4())
        request.description = ""
        request.workflowExecutionRetentionPeriodInDays = 1
        response, err = self.service.register_domain(request)
        self.assertIsNone(response)  # RegisterDomain returns void
        self.assertIsNone(err)

    def test_duplicate_domains(self):
        request = RegisterDomainRequest()
        request.name = str(uuid4())
        request.description = ""
        request.workflowExecutionRetentionPeriodInDays = 1
        response, err = self.service.register_domain(request)
        response, err = self.service.register_domain(request)
        self.assertIsNotNone(err)
        self.assertIsInstance(err, DomainAlreadyExistsError)

    def test_get_workflow_execution_history(self):
        response, err = self.service.start_workflow(self.request)
        request = GetWorkflowExecutionHistoryRequest()
        request.domain = "test-domain"
        request.execution = WorkflowExecution()
        request.execution.workflow_id = self.request.workflow_id
        request.execution.run_id = response.run_id
        response, err = self.service.get_workflow_execution_history(request)
        self.assertIsNone(err)
        self.assertIsNotNone(response)
        self.assertIsNotNone(response.history)
        self.assertIsNotNone(response.history.events)

    def test_poll_for_decision_task(self):
        request = PollForDecisionTaskRequest()
        request.identity = "123@localhost"
        request.domain = "test-domain"
        request.task_list = TaskList()
        request.task_list.name = "test-task-list" + str(uuid4())
        with self.assertRaisesRegex(TChannelException, "timeout") as context:
            self.service.poll_for_decision_task(request)

    def test_respond_decision_task_completed(self):
        request = RespondDecisionTaskCompletedRequest()
        request.task_token = "{}"
        request.identity = "123@localhost"
        response, err = self.service.respond_decision_task_completed(request)
        self.assertIsNotNone(err)
        self.assertIsNone(response)
        self.assertRegex(str(err), "Domain not set")

    def test_respond_decision_task_failed(self):
        request = RespondDecisionTaskFailedRequest()
        request.task_token = "{}"
        request.identity = "123@localhost"
        request.cause = DecisionTaskFailedCause.BAD_REQUEST_CANCEL_ACTIVITY_ATTRIBUTES
        response, err = self.service.respond_decision_task_failed(request)
        self.assertIsNotNone(err)
        self.assertIsNone(response)
        self.assertRegex(str(err), "Domain not set")

    def test_poll_for_activity_task_timeout(self):
        request = PollForActivityTaskRequest()
        request.domain = "test-domain"
        request.identity = WorkflowService.get_identity()
        request.task_list = TaskList()
        request.task_list.name = "test-task-list"
        with self.assertRaisesRegex(TChannelException, "timeout") as context:
            self.service.poll_for_activity_task(request)

    def test_record_activity_task_heartbeat(self):
        request = RecordActivityTaskHeartbeatRequest()
        request.task_token = "{}"
        request.identity = "123@localhost"
        response, err = self.service.record_activity_task_heartbeat(request)
        self.assertIsNotNone(err)
        self.assertRegex(str(err), "Domain not set")

    def test_record_activity_task_heartbeat_by_id(self):
        start_response, _ = self.service.start_workflow(self.request)
        request = RecordActivityTaskHeartbeatByIDRequest()
        request.identity = "123@localhost"
        request.domain = "test-domain"
        request.workflow_id = self.request.workflow_id
        request.run_id = start_response.run_id
        request.activity_id = "dummy-activity-id"
        response, err = self.service.record_activity_task_heartbeat_by_id(request)
        self.assertIsNotNone(err)
        self.assertIsNone(response)
        self.assertRegex(str(err), "No such activityID")

    def test_respond_query_task_completed_invalid(self):
        request = RespondQueryTaskCompletedRequest()
        request.task_token = "{}"
        request.completed_type = QueryTaskCompletedType.COMPLETED
        request.query_result = ""
        response, err = self.service.respond_query_task_completed(request)
        self.assertIsNotNone(err)
        self.assertRegex(str(err), "Invalid TaskToken")

    def test_respond_activity_task_completed_by_id(self):
        start_response, _ = self.service.start_workflow(self.request)
        request = RespondActivityTaskCompletedByIDRequest()
        request.identity = "123@localhost"
        request.domain = "test-domain"
        request.workflow_id = self.request.workflow_id
        request.run_id = start_response.run_id
        request.activity_id = "dummy-activity-id"
        response, err = self.service.respond_activity_task_completed_by_id(request)
        self.assertIsNotNone(err)
        self.assertIsNone(response)
        self.assertRegex(str(err), "No such activityID")

    def test_respond_activity_task_failed(self):
        request = RespondActivityTaskFailedRequest()
        request.task_token = '{"domainId": "%s", "workflowId": "%s"}' % (str(uuid4()), str(uuid4()))
        request.identity = "123@localhost"
        response, err = self.service.respond_activity_task_failed(request)
        self.assertIsNotNone(err)
        self.assertRegex(str(err), "Domain .* does not exist")
        self.assertIsNone(response)

    def test_respond_activity_task_failed_by_id_invalid(self):
        start_response, _ = self.service.start_workflow(self.request)
        request = RespondActivityTaskFailedByIDRequest()
        request.identity = "123@localhost"
        request.domain = "test-domain"
        request.workflow_id = self.request.workflow_id
        request.run_id = start_response.run_id
        request.activity_id = "dummy-activity-id"
        response, err = self.service.respond_activity_task_failed_by_id(request)
        self.assertIsNotNone(err)
        self.assertRegex(str(err), "No such activityID")
        self.assertIsNone(response)

    def test_respond_activity_task_canceled_invalid(self):
        request = RespondActivityTaskCanceledRequest()
        request.task_token = '{"domainId": "%s", "workflowId": "%s"}' % (str(uuid4()), str(uuid4()))
        request.identity = "123@localhost"
        response, err = self.service.respond_activity_task_canceled(request)
        self.assertIsNotNone(err)
        self.assertRegex(str(err), "Domain .* does not exist")
        self.assertIsNone(response)

    def test_respond_activity_task_canceled_by_id_invalid(self):
        start_response, _ = self.service.start_workflow(self.request)
        request = RespondActivityTaskCanceledByIDRequest()
        request.domain = "test-domain"
        request.workflow_id = self.request.workflow_id
        request.run_id = start_response.run_id
        request.activity_id = "dummy-activity-id"
        response, err = self.service.respond_activity_task_canceled_by_id(request)
        self.assertIsNone(response)
        self.assertIsNotNone(err)
        self.assertRegex(str(err), "No such activityID")

    def test_request_cancel_workflow_execution(self):
        start_response, _ = self.service.start_workflow(self.request)
        request = RequestCancelWorkflowExecutionRequest()
        request.domain = "test-domain"
        request.workflow_execution = WorkflowExecution()
        request.workflow_execution.workflow_id = self.request.workflow_id
        request.workflow_execution.run_id = start_response.run_id
        response, err = self.service.request_cancel_workflow_execution(request)
        self.assertIsNone(err)
        self.assertIsNone(response)

    def test_signal_workflow_execution(self):
        start_response, _ = self.service.start_workflow(self.request)
        request = SignalWorkflowExecutionRequest()
        request.domain = "test-domain"
        request.signal_name = "dummy-signal"
        request.workflow_execution = WorkflowExecution()
        request.workflow_execution.workflow_id = self.request.workflow_id
        request.workflow_execution.run_id = start_response.run_id
        response, err = self.service.signal_workflow_execution(request)
        self.assertIsNone(err)
        self.assertIsNone(response)

    def test_signal_with_start_workflow_execution(self):
        request = SignalWithStartWorkflowExecutionRequest()
        request.signal_name = "dummy-signal"
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
        response, err = self.service.signal_with_start_workflow_execution(request)
        self.assertIsNone(err)
        self.assertIsNotNone(response)
        self.assertIsInstance(response, StartWorkflowExecutionResponse)

    def test_terminate_workflow_execution(self):
        start_response, _ = self.service.start_workflow(self.request)
        request = TerminateWorkflowExecutionRequest()
        request.domain = "test-domain"
        request.workflow_execution = WorkflowExecution()
        request.workflow_execution.workflow_id = self.request.workflow_id
        request.workflow_execution.run_id = start_response.run_id
        response, err = self.service.terminate_workflow_execution(request)
        self.assertIsNone(err)
        self.assertIsNone(response)

    def test_list_open_workflow_executions(self):
        request = ListOpenWorkflowExecutionsRequest()
        request.domain = "test-domain"
        request.start_time_filter = StartTimeFilter()
        request.maximum_page_size = 20
        request.start_time_filter.earliest_time = 1
        request.start_time_filter.latest_time = 2 ** 63 - 1
        response, err = self.service.list_open_workflow_executions(request)
        self.assertIsNone(err)
        self.assertIsNotNone(response)
        self.assertIsNotNone(response.executions)

    def test_list_closed_workflow_executions(self):
        request = ListClosedWorkflowExecutionsRequest()
        request.domain = "test-domain"
        request.start_time_filter = StartTimeFilter()
        # Nano seconds?
        request.start_time_filter.earliest_time = calendar.timegm(time.gmtime()) * 1e+9
        request.start_time_filter.latest_time = calendar.timegm(time.gmtime()) * 1e+9

        response, err = self.service.list_closed_workflow_executions(request)
        self.assertIsNone(err)
        self.assertIsNotNone(response)
        self.assertIsInstance(response, ListClosedWorkflowExecutionsResponse)

    def test_reset_sticky_task_list(self):
        start_response, _ = self.service.start_workflow(self.request)
        request = ResetStickyTaskListRequest()
        request.domain = "test-domain"
        request.execution = WorkflowExecution()
        request.execution.workflow_id = self.request.workflow_id
        request.execution.run_id = start_response.run_id
        response, err = self.service.reset_sticky_task_list(request)
        self.assertIsNone(err)
        self.assertIsNotNone(response)

    def test_query_workflow_timeout(self):
        start_response, _ = self.service.start_workflow(self.request)
        request = QueryWorkflowRequest()
        request.domain = "test-domain"
        request.execution = WorkflowExecution()
        request.execution.workflow_id = self.request.workflow_id
        request.execution.run_id = start_response.run_id
        request.query = WorkflowQuery()
        request.query.query_type = "getDummy"
        request.query.query_args = None
        with self.assertRaisesRegex(TChannelException, "timeout") as context:
            self.service.query_workflow(request)

    def test_describe_workflow_execution(self):
        start_response, _ = self.service.start_workflow(self.request)
        request = DescribeWorkflowExecutionRequest()
        request.domain = "test-domain"
        request.execution = WorkflowExecution()
        request.execution.workflow_id = self.request.workflow_id
        request.execution.run_id = start_response.run_id
        response, err = self.service.describe_workflow_execution(request)
        self.assertIsNone(err)
        self.assertIsNotNone(response)
        self.assertIsInstance(response, DescribeWorkflowExecutionResponse)

    def test_describe_workflow_execution_invalid_workflow(self):
        request = DescribeWorkflowExecutionRequest()
        request.domain = "test-domain"
        request.execution = WorkflowExecution()
        request.execution.workflow_id = str(uuid4())
        request.execution.run_id = str(uuid4())
        response, err = self.service.describe_workflow_execution(request)
        self.assertIsNone(response)
        self.assertIsInstance(err, EntityNotExistsError)

    def test_describe_task_list(self):
        request = DescribeTaskListRequest()
        request.task_list = TaskList()
        request.task_list.name = "test-task-list"
        request.task_list_type = TaskListType.Decision
        request.domain = "test-domain"
        response, err = self.service.describe_task_list(request)
        self.assertIsNone(err)
        self.assertIsNotNone(response)
        self.assertIsInstance(response, DescribeTaskListResponse)
        self.assertEqual(0, len(response.pollers))

    def tearDown(self) -> None:
        self.service.connection.close()
