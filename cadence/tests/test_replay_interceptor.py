from unittest.mock import MagicMock, Mock

import pytest

from cadence.decision_loop import DecisionContext, ITask
from cadence.replay_interceptor import make_replay_aware
import cadence.decision_loop

a_captured = None
b_captured = None


@pytest.fixture()
def task_decision_context_replaying():
    task: ITask = Mock()
    task.decider = Mock()
    decision_context = MagicMock()
    decision_context.is_replaying = Mock(return_value=True)
    task.decider.decision_context = decision_context
    return task


@pytest.fixture()
def task_decision_context_not_replaying():
    task: ITask = Mock()
    task.decider = Mock()
    decision_context = MagicMock()
    decision_context.is_replaying = Mock(return_value=False)
    task.decider.decision_context = decision_context
    return task


@pytest.fixture()
def target():
    return Target()

class Target:
    def do_stuff(self, a, b=1):
        global a_captured, b_captured
        a_captured = a
        b_captured = b


@pytest.mark.asyncio
async def test_get_replay_aware_interceptor_not_replaying(task_decision_context_not_replaying, target: Target):
    cadence.decision_loop.current_task.set(task_decision_context_not_replaying)
    global a_captured, b_captured
    a_captured = None
    b_captured = None
    target = Target()
    original_fn = target.do_stuff
    make_replay_aware(target)
    assert target.do_stuff != original_fn
    target.do_stuff(20, b=30)
    assert a_captured == 20
    assert b_captured == 30


@pytest.mark.asyncio
async def test_get_replay_aware_interceptor_replaying(task_decision_context_replaying, target: Target):
    cadence.decision_loop.current_task.set(task_decision_context_replaying)
    global a_captured, b_captured
    a_captured = None
    b_captured = None
    original_fn = target.do_stuff
    make_replay_aware(target)
    assert target.do_stuff != original_fn
    target.do_stuff(20, b=30)
    assert a_captured is None
    assert b_captured is None
