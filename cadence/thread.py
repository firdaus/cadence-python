from __future__ import annotations
import threading
import contextvars
from dataclasses import dataclass, field
from enum import Enum
from threading import RLock, Condition
from typing import Callable

from cadence.exceptions import DestroyWorkflowThreadError, IllegalStateException, IllegalArgumentException


class Status(Enum):
    CREATED = 1
    RUNNING = 2
    YIELDED = 3
    EVALUATING = 4
    DONE = 5


current_workflow_thread = contextvars.ContextVar("current_workflow_thread")


@dataclass
class WorkflowThreadContext:
    """
    This is almost a line-by-line translation of the equivalent class in the Cadence Java SDK.
    """
    lock: RLock = None
    yield_reason: str = None
    unhandled_exception: Exception = None
    run_condition: Condition = None
    yield_condition: Condition = None
    evaluation_condition: Condition = None
    status: Status = Status.CREATED
    destroy_requested: bool = False
    in_run_until_blocked: bool = False
    evaluation_function: Callable = None
    remain_blocked: bool = False

    def __post_init__(self):
        self.lock = RLock()
        self.run_condition = Condition(self.lock)
        self.yield_condition = Condition(self.lock)
        self.evaluation_condition = Condition(self.lock)

    def initial_yield(self):
        status: Status = self.get_status()
        if status == Status.DONE:
            raise DestroyWorkflowThreadError("done in initial_yield")
        if status != Status.RUNNING:
            raise IllegalStateException(f"not in RUNNING but in {status} state")
        self.yield_thread("created", lambda: True)

    def yield_thread(self, reason: str, unblock_function: Callable):
        if not unblock_function:
            raise IllegalArgumentException(f"none unblock_function")
        with self.lock:
            try:
                while not self.in_run_until_blocked or not unblock_function():
                    if self.destroy_requested:
                        raise DestroyWorkflowThreadError()
                    self.status = Status.YIELDED
                    self.run_condition.notify()
                    self.yield_condition.wait()
                    self.maybe_evaluate(reason)
                    # Java code sets yield_reason here, not sure why it doesn't set it before the await
                    self.yield_reason = reason
            finally:
                self.set_status(Status.RUNNING)
                self.remain_blocked = False
                self.yield_reason = None

    def maybe_evaluate(self, reason):
        if self.status == Status.EVALUATING:
            try:
                self.evaluation_function(reason)
            except Exception as ex:
                self.evaluation_function(str(ex))
            finally:
                self.status = Status.YIELDED
                self.evaluation_condition.notify()

    def evaluate_in_coroutine_context(self, function: Callable):
        with self.lock:
            try:
                if not function:
                    raise IllegalArgumentException("none function")
                if self.status != Status.YIELDED and self.status != Status.RUNNING:
                    raise IllegalStateException(f"Not in yielded status: {self.status}")
                if self.evaluation_function:
                    raise IllegalStateException("Already evaluating")
                if self.in_run_until_blocked:
                    raise IllegalStateException("Running runUntilBlocked")
                self.evaluation_function = function
                self.status = Status.EVALUATING
                self.yield_condition.notify()
                while self.status == Status.EVALUATING:
                    self.evaluation_condition.wait()
            finally:
                self.evaluation_function = None

    def get_status(self):
        with self.lock:
            return self.status

    def set_status(self, status: Status):
        with self.lock:
            self.status = status
            if self.is_done():
                self.run_condition.notify();

    def is_done(self):
        with self.lock:
            return self.status == Status.DONE

    def set_unhandled_exception(self, ex: Exception):
        with self.lock:
            self.unhandled_exception = ex

    def get_unhandled_exception(self):
        with self.lock:
            return self.unhandled_exception

    def get_yield_reason(self):
        with self.lock:
            return self.yield_reason

    def run_until_blocked(self) -> bool:
        with self.lock:
            try:
                if self.status == Status.DONE:
                    return False
                if self.evaluation_function is not None:
                    raise IllegalStateException("Cannot run_until_blocked while evaluating")
                self.in_run_until_blocked = True
                if self.status != Status.CREATED:
                    self.status = Status.RUNNING
                self.remain_blocked = True
                self.yield_condition.notify()
                while self.status in (Status.RUNNING, Status.CREATED):
                    self.run_condition.wait()
                    if self.evaluation_function is not None:
                        raise IllegalStateException("Cannot run_until_blocked while evaluating")
                return not self.remain_blocked
            finally:
                self.in_run_until_blocked = False

    def is_destroy_requested(self):
        with self.lock:
            return self.destroy_requested

    def destroy(self):
        with self.lock:
            self.destroy_requested = True
            if self.status in (Status.CREATED, Status.RUNNING, Status.DONE):
                self.status = Status.DONE
                return

        def fn(*args):
            raise DestroyWorkflowThreadError()

        self.evaluate_in_coroutine_context(fn)
        self.run_until_blocked()


@dataclass
class WorkflowThread:

    @staticmethod
    def current() -> WorkflowThread:
        return current_workflow_thread.get()

    workflow_proc: Callable
    context: WorkflowThreadContext = field(default_factory=WorkflowThreadContext)
    thread_name: str = None
    thread: threading.Thread = None

    def start(self):
        if self.context.status != Status.CREATED:
            raise Exception("Already started")
        self.context.set_status(Status.RUNNING)
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def run(self):
        ctx = contextvars.copy_context()
        ctx.run(current_workflow_thread.set, self)
        ctx.run(self.run_workflow_proc)

    def run_workflow_proc(self):
        if self.thread_name:
            self.thread.name = self.thread_name
        try:
            self.context.initial_yield()
            self.workflow_proc()
        except DestroyWorkflowThreadError as ex:
            if not self.context.is_destroy_requested():
                self.context.set_unhandled_exception(ex)
        except BaseException as ex:
            self.context.set_unhandled_exception(ex)
        finally:
            self.context.set_status(Status.DONE)
