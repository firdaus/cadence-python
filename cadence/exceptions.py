from cadence.cadence_types import TimeoutType


class IllegalStateException(BaseException):
    pass


class IllegalArgumentException(BaseException):
    pass


class WorkflowTypeNotFound(Exception):
    pass


class NonDeterministicWorkflowException(BaseException):
    pass


class ActivityTaskFailedException(Exception):

    def __init__(self, reason: str, details: bytes) -> None:
        super().__init__(reason)
        self.reason = reason
        self.details = details


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
