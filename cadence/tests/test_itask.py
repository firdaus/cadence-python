import asyncio
from asyncio.events import AbstractEventLoop
from unittest import TestCase
from unittest.mock import Mock, MagicMock

from cadence.decision_loop import ReplayDecider, ITask
from cadence.tests.test_decision_context import run_once


class TestAwaitTill(TestCase):

    def setUp(self) -> None:
        self.event_loop: AbstractEventLoop = asyncio.get_event_loop()
        self.decider: ReplayDecider = Mock()
        self.decider.get_and_increment_next_id = MagicMock(return_value="0")
        self.decider.event_loop = Mock()
        self.future = self.event_loop.create_future()
        self.decider.event_loop.create_future = MagicMock(return_value=self.future)
        self.itask = ITask(decider=self.decider)

    def tearDown(self) -> None:
        self.task.cancel()

    def test_await_till(self):
        self.task = self.event_loop.create_task(self.itask.await_till(lambda *args: None))
        run_once(self.event_loop)
        assert self.itask.awaited

    def test_await_till_no_progress(self):
        self.task = self.event_loop.create_task(self.itask.await_till(lambda *args: None))
        run_once(self.event_loop)
        assert self.itask.awaited
        run_once(self.event_loop)
        assert self.itask.awaited

    def test_unblock(self):
        blocked = True

        def check_blocked():
            nonlocal blocked
            return not blocked

        self.task = self.event_loop.create_task(self.itask.await_till(check_blocked))
        run_once(self.event_loop)
        blocked = False
        self.itask.unblock()
        run_once(self.event_loop)
        assert not self.itask.awaited
