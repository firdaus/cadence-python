import json
from unittest.mock import MagicMock, Mock

import pytest

from cadence.cadence_types import HistoryEvent, WorkflowExecutionSignaledEventAttributes
from cadence.decision_loop import ReplayDecider, WorkflowMethodTask, Status
from cadence.worker import Worker
from cadence.workflow import signal_method


@pytest.fixture
def workflow_instance():
    return DummyWorkflow()


@pytest.fixture
def workflow_task(decider, workflow_instance):
    workflow_task = WorkflowMethodTask(task_id=decider.execution_id, workflow_input=None,
                                       worker=decider.worker, workflow_type=Mock(), decider=decider)
    decider.workflow_task = workflow_task
    workflow_task.workflow_instance = workflow_instance
    return workflow_task


@pytest.fixture
def worker():
    worker = Worker()
    worker.register_workflow_implementation_type(DummyWorkflow)
    return worker


@pytest.fixture
def decider(worker):
    return ReplayDecider("run-id", MagicMock(), worker)


class DummyWorkflow:
    @signal_method
    def the_signal_method(self, name, age):
        pass


def test_handle_workflow_execution_signaled(decider, workflow_task):
    assert isinstance(MagicMock, object)
    event = HistoryEvent()
    event.workflow_execution_signaled_event_attributes = WorkflowExecutionSignaledEventAttributes()
    event.workflow_execution_signaled_event_attributes.signal_name = "DummyWorkflow::the_signal_method"
    event.workflow_execution_signaled_event_attributes.input = json.dumps(["bob", 28]);
    decider.handle_workflow_execution_signaled(event)
    assert decider.tasks
    task = decider.tasks[0]
    assert task.signal_name == "DummyWorkflow::the_signal_method"
    assert task.signal_input == ["bob", 28]
    assert task.workflow_task == workflow_task
    assert task.decider == decider
    assert task.task_id == "run-id"
    assert task.status == Status.CREATED
