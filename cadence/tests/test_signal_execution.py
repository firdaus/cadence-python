from unittest.mock import MagicMock

import pytest

from cadence.decision_loop import SignalTask, Status, current_workflow_task
from cadence.exceptions import SignalNotFound


class DummyWorkflow:

    def __init__(self):
        self.signal_invoked = False
        self.args = None

    async def signal(self, *args):
        self.invoked = True
        self.args = args


@pytest.fixture()
def workflow_instance():
    workflow = DummyWorkflow()
    workflow._signal_methods = {
        "signal": DummyWorkflow.signal
    }
    return workflow


@pytest.fixture()
def workflow_task():
    return MagicMock()


@pytest.fixture()
def decider():
    return MagicMock()


@pytest.fixture()
def signal_task(workflow_instance, workflow_task, decider):
    task = SignalTask(task_id="task_id", workflow_instance=workflow_instance, signal_name="signal", signal_input=[1, 2, 3], workflow_task=workflow_task, decider=decider)
    return task


@pytest.mark.asyncio
async def test_signal_invoked(signal_task, workflow_instance):
    await signal_task.signal_main()
    assert workflow_instance.invoked
    assert list(workflow_instance.args) == [1, 2, 3]


@pytest.mark.asyncio
async def test_signal_done(signal_task):
    await signal_task.signal_main()
    assert signal_task.status == Status.DONE


@pytest.mark.asyncio
async def test_signal_created(signal_task):
    assert signal_task.status == Status.CREATED


@pytest.mark.asyncio
async def test_signal_set_current_workflow(signal_task, workflow_task):
    await signal_task.signal_main()
    assert current_workflow_task.get() == workflow_task


@pytest.mark.asyncio
async def test_signal_complete_workflow_execution_invoked(signal_task, decider):
    await signal_task.signal_main()
    decider.complete_signal_execution.assert_called_with(signal_task)


@pytest.mark.asyncio
async def test_signal_notfound(signal_task):
    signal_task.signal_name = "blah"
    await signal_task.signal_main()
    assert signal_task.status == Status.DONE
    assert isinstance(signal_task.exception_thrown, SignalNotFound)


@pytest.mark.asyncio
async def test_signal_start(signal_task):
    signal_task.start()
    assert signal_task.task
