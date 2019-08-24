from unittest.mock import MagicMock, Mock

import pytest

from cadence.decision_loop import ReplayDecider, SignalMethodTask
from cadence.worker import Worker


@pytest.fixture
def worker():
    worker = Worker()
    return worker


@pytest.fixture
def decider(worker):
    return ReplayDecider("run-id", MagicMock(), worker)


def test_complete_signal_execution(decider):
    task = Mock()
    decider.signal_tasks.append(task)
    decider.complete_signal_execution(task)
    assert len(decider.signal_tasks) == 0
    task.destroy.assert_called_once()
