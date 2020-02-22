from unittest.mock import Mock, MagicMock

import json

import pytest

from cadence.cadence_types import QueryWorkflowResponse, WorkflowExecution, QueryWorkflowRequest, QueryRejected, \
    WorkflowExecutionCloseStatus, WorkflowType, PollForDecisionTaskResponse, WorkflowQuery, \
    RespondQueryTaskCompletedRequest
from cadence.decision_loop import ReplayDecider, Status, QueryMethodTask, DecisionTaskLoop
from cadence.exceptions import QueryRejectedException, QueryDidNotComplete
from cadence.worker import _get_qm, Worker
from cadence.workflow import query_method, QueryMethod, WorkflowClient, exec_query
from cadence.workflowservice import WorkflowService


class DummyException(Exception):
    pass


class DummyWorkflow:
    @query_method
    def dummy_query(self):
        pass

    @query_method()
    def dummy_query_paren(self):
        pass

    @query_method(name="blah")
    def dummy_query_paren_custom_name(self):
        pass


class DummyWorkflowImpl(DummyWorkflow):
    def dummy_query(self):
        pass

    def dummy_query_paren(self):
        pass

    def dummy_query_paren_custom_name(self):
        pass


def test_query_no_paren():
    assert DummyWorkflow.dummy_query._query_method
    assert DummyWorkflow.dummy_query._query_method.name == "DummyWorkflow::dummy_query"


def test_query_paren():
    assert DummyWorkflow.dummy_query_paren._query_method
    assert DummyWorkflow.dummy_query_paren._query_method.name == "DummyWorkflow::dummy_query_paren"


def test_query_paren_custom_name():
    # TODO: Double check whether this is the correct behavior
    assert DummyWorkflow.dummy_query_paren_custom_name._query_method
    assert DummyWorkflow.dummy_query_paren_custom_name._query_method.name == "blah"


def test_get_qm():
    assert isinstance(_get_qm(DummyWorkflowImpl, "dummy_query"), QueryMethod)
    assert isinstance(_get_qm(DummyWorkflowImpl, "dummy_query_paren"), QueryMethod)
    assert isinstance(_get_qm(DummyWorkflowImpl, "dummy_query_paren_custom_name"), QueryMethod)


def test_worker_register_query_method():
    worker = Worker()
    worker.register_workflow_implementation_type(DummyWorkflowImpl, "DummyWorkflow")
    assert DummyWorkflowImpl._query_methods
    assert "DummyWorkflow::dummy_query" in DummyWorkflowImpl._query_methods
    assert "DummyWorkflow::dummyQuery" in DummyWorkflowImpl._query_methods
    assert "DummyWorkflow::dummy_query_paren" in DummyWorkflowImpl._query_methods
    assert "DummyWorkflow::dummyQueryParen" in DummyWorkflowImpl._query_methods
    assert "blah" in DummyWorkflowImpl._query_methods


def test_workflow_query_stub():
    client = WorkflowClient(service=Mock(), domain="", options=None)
    stub: DummyWorkflow = client.new_workflow_stub(DummyWorkflow)
    assert stub.dummy_query != DummyWorkflow.dummy_query
    assert stub.dummy_query._query_method


def test_exec_query():
    stub = Mock()
    stub._execution = WorkflowExecution()

    response = QueryWorkflowResponse()
    response.query_result = '"blah"'
    workflow_client = Mock()
    workflow_client.domain = "the-domain"
    workflow_client.service = Mock()
    workflow_client.service.query_workflow = MagicMock(return_value=(response, None))

    ret = exec_query(workflow_client, QueryMethod(name="the_query_method"), [1, 2, 3], stub)
    assert ret == "blah"
    args, kwargs = workflow_client.service.query_workflow.call_args_list[0]
    request: QueryWorkflowRequest = args[0]
    assert request.execution is stub._execution
    assert request.query.query_type == "the_query_method"
    assert request.query.query_args == json.dumps([1, 2, 3])
    assert request.domain == "the-domain"


def test_exec_query_query_rejected():
    stub = Mock()
    stub._execution = WorkflowExecution()

    response = QueryWorkflowResponse()
    response.query_rejected = QueryRejected(close_status=WorkflowExecutionCloseStatus.COMPLETED)

    workflow_client = Mock()
    workflow_client.domain = "the-domain"
    workflow_client.service = Mock()
    workflow_client.service.query_workflow = MagicMock(return_value=(response, None))

    with pytest.raises(QueryRejectedException) as exc_info:
        exec_query(workflow_client, QueryMethod(name="the_query_method"), [1, 2, 3], stub)
    assert exc_info.value.close_status == WorkflowExecutionCloseStatus.COMPLETED


def mock_decision_task():
    decision_task = PollForDecisionTaskResponse()
    decision_task.query = WorkflowQuery()
    decision_task.query.query_args = "[1, 2, 3]"
    decision_task.query.query_type = "the-query-method"
    return decision_task


def mock_decider(run_event_loop_once):
    worker = Mock()
    decider = ReplayDecider("execution-id", WorkflowType(name="workflow-type"), worker)
    decider.event_loop = Mock()
    decider.event_loop.run_event_loop_once = run_event_loop_once
    decider.workflow_task = Mock()
    decider.service = Mock()
    return decider


def test_replay_decider_query():
    def run_event_loop_once(*args):
        decider.tasks[0].status = Status.DONE
        decider.tasks[0].ret_value = "abc"

    decider = mock_decider(run_event_loop_once)
    decision_task = mock_decision_task()
    ret = decider.query(decision_task, decision_task.query)
    assert ret == "abc"

    query_task: QueryMethodTask = decider.tasks[0]
    assert query_task.query_name == "the-query-method"
    assert query_task.query_input == [1, 2, 3]


def test_replay_decider_query_exception():
    def run_event_loop_once(*args):
        task: QueryMethodTask = decider.tasks[0]
        task.status = Status.DONE
        task.exception_thrown = DummyException("blah")

    decider = mock_decider(run_event_loop_once)
    decision_task = mock_decision_task()
    with pytest.raises(DummyException):
        decider.query(decision_task, decision_task.query)


def test_replay_decider_query_did_not_complete():
    def run_event_loop_once(*args):
        pass

    decider = mock_decider(run_event_loop_once)
    decision_task = mock_decision_task()
    with pytest.raises(QueryDidNotComplete):
        decider.query(decision_task, decision_task.query)


def test_replay_decider_respond_query():
    service: WorkflowService = Mock()
    service.respond_query_task_completed = Mock(return_value=(None, None))
    decision_task_loop = DecisionTaskLoop(worker=Mock(), service=service)
    decision_task_loop.respond_query(task_token=b"the-task-token",
                                     result=b"the-result", error_message=None)
    service.respond_query_task_completed.assert_called_once()
    args, kwargs = service.respond_query_task_completed.call_args_list[0]
    request = args[0]
    assert isinstance(request, RespondQueryTaskCompletedRequest)
    assert request.task_token == b"the-task-token"
    assert request.query_result == b"the-result"


def test_replay_decider_respond_query_error():
    service: WorkflowService = Mock()
    service.respond_query_task_completed = Mock(return_value=(None, None))
    decision_task_loop = DecisionTaskLoop(worker=Mock(), service=service)
    decision_task_loop.respond_query(task_token=b"the-task-token",
                                     result=None, error_message=b"the-error")
    service.respond_query_task_completed.assert_called_once()
    args, kwargs = service.respond_query_task_completed.call_args_list[0]
    request = args[0]
    assert isinstance(request, RespondQueryTaskCompletedRequest)
    assert request.task_token == b"the-task-token"
    assert request.error_message == b"the-error"


@pytest.mark.asyncio
async def test_query_method_task():
    async def get_stuff(self):
        return "the-return-value"

    workflow_instance = Mock()
    workflow_instance._query_methods = {
        "Workflow::get_stuff": get_stuff
    }
    task = QueryMethodTask(task_id="dummy-task-id",
                           workflow_instance=workflow_instance,
                           query_name="Workflow::get_stuff",
                           query_input=[])
    await task.query_main()
    assert task.status == Status.DONE
    assert task.ret_value == "the-return-value"


@pytest.mark.asyncio
async def test_query_method_task_exception():
    async def get_stuff(self):
        raise DummyException("dummy")

    workflow_instance = Mock()
    workflow_instance._query_methods = {
        "Workflow::get_stuff": get_stuff
    }
    task = QueryMethodTask(task_id="dummy-task-id",
                           workflow_instance=workflow_instance,
                           query_name="Workflow::get_stuff",
                           query_input=[])
    await task.query_main()
    assert task.status == Status.DONE
    assert task.ret_value is None
    assert isinstance(task.exception_thrown, DummyException)


@pytest.mark.asyncio
async def test_query_method_task_args():
    captured_arg1 = None
    captured_arg2 = None

    async def get_stuff(self, arg1, arg2):
        nonlocal captured_arg1, captured_arg2
        captured_arg1 = arg1
        captured_arg2 = arg2

    workflow_instance = Mock()
    workflow_instance._query_methods = {
        "Workflow::get_stuff": get_stuff
    }
    task = QueryMethodTask(task_id="dummy-task-id",
                           workflow_instance=workflow_instance,
                           query_name="Workflow::get_stuff",
                           query_input=["first-argument", "second-argument"])
    await task.query_main()
    assert captured_arg1 == "first-argument"
    assert captured_arg2 == "second-argument"
