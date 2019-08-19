import asyncio
from unittest.mock import Mock, MagicMock

import pytest

from cadence.decision_loop import ReplayDecider, DecisionContext


@pytest.fixture
def event_loop():
    return asyncio.get_event_loop()


@pytest.fixture
def decision_context(event_loop):
    decider: ReplayDecider = Mock()
    decider.get_and_increment_next_id = MagicMock(return_value="0")
    decider.event_loop = event_loop
    decision_context = DecisionContext(decider=decider)
    decider.decision_context = decision_context
    return decision_context
