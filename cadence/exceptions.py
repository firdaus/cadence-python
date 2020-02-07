from dataclasses import dataclass

from cadence.cadence_types import TimeoutType, ActivityType, WorkflowExecution


class IllegalStateException(BaseException):
    pass


class IllegalArgumentException(BaseException):
    pass


class WorkflowTypeNotFound(Exception):
    pass


class NonDeterministicWorkflowException(BaseException):
    pass


class ActivityTaskFailedException(Exception):

    def __init__(self, reason: str, cause: Exception) -> None:
        super().__init__(reason)
        self.reason = reason
        self.cause = cause


class ActivityTaskTimeoutException(Exception):

    def __init__(self, event_id: int, timeout_type: TimeoutType, details: bytes, *args: object) -> None:
        super().__init__(*args)
        self.details = details
        self.timeout_type = timeout_type
        self.event_id = event_id


class SignalNotFound(Exception):
    pass


class CancellationException(Exception):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cause = None

    def init_cause(self, cause):
        self.cause = cause


class ActivityCancelledException(Exception):
    pass


@dataclass
class WorkflowOperationException(Exception):
    event_id: int = None


@dataclass
class ActivityException(WorkflowOperationException):
    activity_type: ActivityType = None
    activity_id: str = ""

    def __str__(self):
        return f'{type(self).__name__}  ActivityType="{self.activity_type.name}", ActivityID="{self.activity_id}", ' \
               f'EventID={self.event_id} '


@dataclass
class ActivityFailureException(ActivityException):
    attempt: int = None
    backoff: int = 0


@dataclass
class WorkflowException(Exception):
    workflow_type: str = None
    execution: WorkflowExecution = None

    def __str__(self):
        return f'{type(self).__name__}: WorkflowType="{self.workflow_type}", ' \
               f'WorkflowID="{self.execution.workflow_id}", RunID="{self.execution.run_id} '


@dataclass
class WorkflowFailureException(WorkflowException):
    decision_task_completed_event_id: int = None
