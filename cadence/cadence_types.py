from __future__ import annotations
from typing import List, Dict
from dataclasses import dataclass, field
from enum import IntEnum


# noinspection PyPep8
@dataclass
class BadRequestError:
    message: str = None
    

# noinspection PyPep8
@dataclass
class InternalServiceError:
    message: str = None
    

# noinspection PyPep8
@dataclass
class DomainAlreadyExistsError:
    message: str = None
    

# noinspection PyPep8
@dataclass
class WorkflowExecutionAlreadyStartedError:
    message: str = None
    start_request_id: str = None
    run_id: str = None
    

# noinspection PyPep8
@dataclass
class EntityNotExistsError:
    message: str = None
    

# noinspection PyPep8
@dataclass
class ServiceBusyError:
    message: str = None
    

# noinspection PyPep8
@dataclass
class CancellationAlreadyRequestedError:
    message: str = None
    

# noinspection PyPep8
@dataclass
class QueryFailedError:
    message: str = None
    

# noinspection PyPep8
@dataclass
class DomainNotActiveError:
    message: str = None
    domain_name: str = None
    current_cluster: str = None
    active_cluster: str = None
    

# noinspection PyPep8
@dataclass
class LimitExceededError:
    message: str = None
    

# noinspection PyPep8
@dataclass
class AccessDeniedError:
    message: str = None
    

# noinspection PyPep8
@dataclass
class RetryTaskError:
    message: str = None
    domain_id: str = None
    workflow_id: str = None
    run_id: str = None
    next_event_id: int = None
    

# noinspection PyPep8
@dataclass
class ClientVersionNotSupportedError:
    feature_version: str = None
    client_impl: str = None
    supported_versions: str = None
    

class WorkflowIdReusePolicy(IntEnum):
    AllowDuplicateFailedOnly = 0
    AllowDuplicate = 1
    RejectDuplicate = 2
    
    @classmethod
    def value_for(cls, n: int) -> WorkflowIdReusePolicy:
        return next(filter(lambda i: i == n, cls), None)

    
class DomainStatus(IntEnum):
    REGISTERED = 0
    DEPRECATED = 1
    DELETED = 2
    
    @classmethod
    def value_for(cls, n: int) -> DomainStatus:
        return next(filter(lambda i: i == n, cls), None)

    
class TimeoutType(IntEnum):
    START_TO_CLOSE = 0
    SCHEDULE_TO_START = 1
    SCHEDULE_TO_CLOSE = 2
    HEARTBEAT = 3
    
    @classmethod
    def value_for(cls, n: int) -> TimeoutType:
        return next(filter(lambda i: i == n, cls), None)

    
class DecisionType(IntEnum):
    ScheduleActivityTask = 0
    RequestCancelActivityTask = 1
    StartTimer = 2
    CompleteWorkflowExecution = 3
    FailWorkflowExecution = 4
    CancelTimer = 5
    CancelWorkflowExecution = 6
    RequestCancelExternalWorkflowExecution = 7
    RecordMarker = 8
    ContinueAsNewWorkflowExecution = 9
    StartChildWorkflowExecution = 10
    SignalExternalWorkflowExecution = 11
    UpsertWorkflowSearchAttributes = 12
    
    @classmethod
    def value_for(cls, n: int) -> DecisionType:
        return next(filter(lambda i: i == n, cls), None)

    
class EventType(IntEnum):
    WorkflowExecutionStarted = 0
    WorkflowExecutionCompleted = 1
    WorkflowExecutionFailed = 2
    WorkflowExecutionTimedOut = 3
    DecisionTaskScheduled = 4
    DecisionTaskStarted = 5
    DecisionTaskCompleted = 6
    DecisionTaskTimedOut = 7
    DecisionTaskFailed = 8
    ActivityTaskScheduled = 9
    ActivityTaskStarted = 10
    ActivityTaskCompleted = 11
    ActivityTaskFailed = 12
    ActivityTaskTimedOut = 13
    ActivityTaskCancelRequested = 14
    RequestCancelActivityTaskFailed = 15
    ActivityTaskCanceled = 16
    TimerStarted = 17
    TimerFired = 18
    CancelTimerFailed = 19
    TimerCanceled = 20
    WorkflowExecutionCancelRequested = 21
    WorkflowExecutionCanceled = 22
    RequestCancelExternalWorkflowExecutionInitiated = 23
    RequestCancelExternalWorkflowExecutionFailed = 24
    ExternalWorkflowExecutionCancelRequested = 25
    MarkerRecorded = 26
    WorkflowExecutionSignaled = 27
    WorkflowExecutionTerminated = 28
    WorkflowExecutionContinuedAsNew = 29
    StartChildWorkflowExecutionInitiated = 30
    StartChildWorkflowExecutionFailed = 31
    ChildWorkflowExecutionStarted = 32
    ChildWorkflowExecutionCompleted = 33
    ChildWorkflowExecutionFailed = 34
    ChildWorkflowExecutionCanceled = 35
    ChildWorkflowExecutionTimedOut = 36
    ChildWorkflowExecutionTerminated = 37
    SignalExternalWorkflowExecutionInitiated = 38
    SignalExternalWorkflowExecutionFailed = 39
    ExternalWorkflowExecutionSignaled = 40
    UpsertWorkflowSearchAttributes = 41
    
    @classmethod
    def value_for(cls, n: int) -> EventType:
        return next(filter(lambda i: i == n, cls), None)

    
class DecisionTaskFailedCause(IntEnum):
    UNHANDLED_DECISION = 0
    BAD_SCHEDULE_ACTIVITY_ATTRIBUTES = 1
    BAD_REQUEST_CANCEL_ACTIVITY_ATTRIBUTES = 2
    BAD_START_TIMER_ATTRIBUTES = 3
    BAD_CANCEL_TIMER_ATTRIBUTES = 4
    BAD_RECORD_MARKER_ATTRIBUTES = 5
    BAD_COMPLETE_WORKFLOW_EXECUTION_ATTRIBUTES = 6
    BAD_FAIL_WORKFLOW_EXECUTION_ATTRIBUTES = 7
    BAD_CANCEL_WORKFLOW_EXECUTION_ATTRIBUTES = 8
    BAD_REQUEST_CANCEL_EXTERNAL_WORKFLOW_EXECUTION_ATTRIBUTES = 9
    BAD_CONTINUE_AS_NEW_ATTRIBUTES = 10
    START_TIMER_DUPLICATE_ID = 11
    RESET_STICKY_TASKLIST = 12
    WORKFLOW_WORKER_UNHANDLED_FAILURE = 13
    BAD_SIGNAL_WORKFLOW_EXECUTION_ATTRIBUTES = 14
    BAD_START_CHILD_EXECUTION_ATTRIBUTES = 15
    FORCE_CLOSE_DECISION = 16
    FAILOVER_CLOSE_DECISION = 17
    BAD_SIGNAL_INPUT_SIZE = 18
    RESET_WORKFLOW = 19
    BAD_BINARY = 20
    SCHEDULE_ACTIVITY_DUPLICATE_ID = 21
    BAD_SEARCH_ATTRIBUTES = 22
    
    @classmethod
    def value_for(cls, n: int) -> DecisionTaskFailedCause:
        return next(filter(lambda i: i == n, cls), None)

    
class CancelExternalWorkflowExecutionFailedCause(IntEnum):
    UNKNOWN_EXTERNAL_WORKFLOW_EXECUTION = 0
    
    @classmethod
    def value_for(cls, n: int) -> CancelExternalWorkflowExecutionFailedCause:
        return next(filter(lambda i: i == n, cls), None)

    
class SignalExternalWorkflowExecutionFailedCause(IntEnum):
    UNKNOWN_EXTERNAL_WORKFLOW_EXECUTION = 0
    
    @classmethod
    def value_for(cls, n: int) -> SignalExternalWorkflowExecutionFailedCause:
        return next(filter(lambda i: i == n, cls), None)

    
class ChildWorkflowExecutionFailedCause(IntEnum):
    WORKFLOW_ALREADY_RUNNING = 0
    
    @classmethod
    def value_for(cls, n: int) -> ChildWorkflowExecutionFailedCause:
        return next(filter(lambda i: i == n, cls), None)

    
class WorkflowExecutionCloseStatus(IntEnum):
    COMPLETED = 0
    FAILED = 1
    CANCELED = 2
    TERMINATED = 3
    CONTINUED_AS_NEW = 4
    TIMED_OUT = 5
    
    @classmethod
    def value_for(cls, n: int) -> WorkflowExecutionCloseStatus:
        return next(filter(lambda i: i == n, cls), None)

    
class ChildPolicy(IntEnum):
    TERMINATE = 0
    REQUEST_CANCEL = 1
    ABANDON = 2
    
    @classmethod
    def value_for(cls, n: int) -> ChildPolicy:
        return next(filter(lambda i: i == n, cls), None)

    
class QueryTaskCompletedType(IntEnum):
    COMPLETED = 0
    FAILED = 1
    
    @classmethod
    def value_for(cls, n: int) -> QueryTaskCompletedType:
        return next(filter(lambda i: i == n, cls), None)

    
class PendingActivityState(IntEnum):
    SCHEDULED = 0
    STARTED = 1
    CANCEL_REQUESTED = 2
    
    @classmethod
    def value_for(cls, n: int) -> PendingActivityState:
        return next(filter(lambda i: i == n, cls), None)

    
class HistoryEventFilterType(IntEnum):
    ALL_EVENT = 0
    CLOSE_EVENT = 1
    
    @classmethod
    def value_for(cls, n: int) -> HistoryEventFilterType:
        return next(filter(lambda i: i == n, cls), None)

    
class TaskListKind(IntEnum):
    NORMAL = 0
    STICKY = 1
    
    @classmethod
    def value_for(cls, n: int) -> TaskListKind:
        return next(filter(lambda i: i == n, cls), None)

    
class ArchivalStatus(IntEnum):
    DISABLED = 0
    ENABLED = 1
    
    @classmethod
    def value_for(cls, n: int) -> ArchivalStatus:
        return next(filter(lambda i: i == n, cls), None)

    
class IndexedValueType(IntEnum):
    STRING = 0
    KEYWORD = 1
    INT = 2
    DOUBLE = 3
    BOOL = 4
    DATETIME = 5
    
    @classmethod
    def value_for(cls, n: int) -> IndexedValueType:
        return next(filter(lambda i: i == n, cls), None)

    
class EncodingType(IntEnum):
    ThriftRW = 0
    
    @classmethod
    def value_for(cls, n: int) -> EncodingType:
        return next(filter(lambda i: i == n, cls), None)

    
class QueryRejectCondition(IntEnum):
    NOT_OPEN = 0
    NOT_COMPLETED_CLEANLY = 1
    
    @classmethod
    def value_for(cls, n: int) -> QueryRejectCondition:
        return next(filter(lambda i: i == n, cls), None)

    
class ContinueAsNewInitiator(IntEnum):
    Decider = 0
    RetryPolicy = 1
    CronSchedule = 2
    
    @classmethod
    def value_for(cls, n: int) -> ContinueAsNewInitiator:
        return next(filter(lambda i: i == n, cls), None)

    
class TaskListType(IntEnum):
    Decision = 0
    Activity = 1
    
    @classmethod
    def value_for(cls, n: int) -> TaskListType:
        return next(filter(lambda i: i == n, cls), None)

    
# noinspection PyPep8
@dataclass
class Header:
    fields: Dict[str, bytes] = field(default_factory=dict)
    

# noinspection PyPep8
@dataclass
class WorkflowType:
    name: str = None
    

# noinspection PyPep8
@dataclass
class ActivityType:
    name: str = None
    

# noinspection PyPep8
@dataclass
class TaskList:
    name: str = None
    kind: TaskListKind = None
    

# noinspection PyPep8
@dataclass
class DataBlob:
    encoding_type: EncodingType = None
    data: bytes = None
    

# noinspection PyPep8
@dataclass
class ReplicationInfo:
    version: int = None
    last_event_id: int = None
    

# noinspection PyPep8
@dataclass
class TaskListMetadata:
    max_tasks_per_second: float = None
    

# noinspection PyPep8
@dataclass
class WorkflowExecution:
    workflow_id: str = None
    run_id: str = None
    

# noinspection PyPep8
@dataclass
class Memo:
    fields: Dict[str, bytes] = field(default_factory=dict)
    

# noinspection PyPep8
@dataclass
class SearchAttributes:
    indexed_fields: Dict[str, bytes] = field(default_factory=dict)
    

# noinspection PyPep8
@dataclass
class WorkflowExecutionInfo:
    execution: WorkflowExecution = None
    type: WorkflowType = None
    start_time: int = None
    close_time: int = None
    close_status: WorkflowExecutionCloseStatus = None
    history_length: int = None
    parent_domain_id: str = None
    parent_execution: WorkflowExecution = None
    execution_time: int = None
    memo: Memo = None
    search_attributes: SearchAttributes = None
    auto_reset_points: ResetPoints = None
    

# noinspection PyPep8
@dataclass
class WorkflowExecutionConfiguration:
    task_list: TaskList = None
    execution_start_to_close_timeout_seconds: int = None
    task_start_to_close_timeout_seconds: int = None
    child_policy: ChildPolicy = None
    

# noinspection PyPep8
@dataclass
class TransientDecisionInfo:
    scheduled_event: HistoryEvent = None
    started_event: HistoryEvent = None
    

# noinspection PyPep8
@dataclass
class ScheduleActivityTaskDecisionAttributes:
    activity_id: str = None
    activity_type: ActivityType = None
    domain: str = None
    task_list: TaskList = None
    input: bytes = None
    schedule_to_close_timeout_seconds: int = None
    schedule_to_start_timeout_seconds: int = None
    start_to_close_timeout_seconds: int = None
    heartbeat_timeout_seconds: int = None
    retry_policy: RetryPolicy = None
    header: Header = None
    

# noinspection PyPep8
@dataclass
class RequestCancelActivityTaskDecisionAttributes:
    activity_id: str = None
    

# noinspection PyPep8
@dataclass
class StartTimerDecisionAttributes:
    timer_id: str = None
    start_to_fire_timeout_seconds: int = None
    

# noinspection PyPep8
@dataclass
class CompleteWorkflowExecutionDecisionAttributes:
    result: bytes = None
    

# noinspection PyPep8
@dataclass
class FailWorkflowExecutionDecisionAttributes:
    reason: str = None
    details: bytes = None
    

# noinspection PyPep8
@dataclass
class CancelTimerDecisionAttributes:
    timer_id: str = None
    

# noinspection PyPep8
@dataclass
class CancelWorkflowExecutionDecisionAttributes:
    details: bytes = None
    

# noinspection PyPep8
@dataclass
class RequestCancelExternalWorkflowExecutionDecisionAttributes:
    domain: str = None
    workflow_id: str = None
    run_id: str = None
    control: bytes = None
    child_workflow_only: bool = None
    

# noinspection PyPep8
@dataclass
class SignalExternalWorkflowExecutionDecisionAttributes:
    domain: str = None
    execution: WorkflowExecution = None
    signal_name: str = None
    input: bytes = None
    control: bytes = None
    child_workflow_only: bool = None
    

# noinspection PyPep8
@dataclass
class UpsertWorkflowSearchAttributesDecisionAttributes:
    search_attributes: SearchAttributes = None
    

# noinspection PyPep8
@dataclass
class RecordMarkerDecisionAttributes:
    marker_name: str = None
    details: bytes = None
    header: Header = None
    

# noinspection PyPep8
@dataclass
class ContinueAsNewWorkflowExecutionDecisionAttributes:
    workflow_type: WorkflowType = None
    task_list: TaskList = None
    input: bytes = None
    execution_start_to_close_timeout_seconds: int = None
    task_start_to_close_timeout_seconds: int = None
    backoff_start_interval_in_seconds: int = None
    retry_policy: RetryPolicy = None
    initiator: ContinueAsNewInitiator = None
    failure_reason: str = None
    failure_details: bytes = None
    last_completion_result: bytes = None
    cron_schedule: str = None
    header: Header = None
    memo: Memo = None
    search_attributes: SearchAttributes = None
    

# noinspection PyPep8
@dataclass
class StartChildWorkflowExecutionDecisionAttributes:
    domain: str = None
    workflow_id: str = None
    workflow_type: WorkflowType = None
    task_list: TaskList = None
    input: bytes = None
    execution_start_to_close_timeout_seconds: int = None
    task_start_to_close_timeout_seconds: int = None
    child_policy: ChildPolicy = None
    control: bytes = None
    workflow_id_reuse_policy: WorkflowIdReusePolicy = None
    retry_policy: RetryPolicy = None
    cron_schedule: str = None
    header: Header = None
    memo: Memo = None
    search_attributes: SearchAttributes = None
    

# noinspection PyPep8
@dataclass
class Decision:
    decision_type: DecisionType = None
    schedule_activity_task_decision_attributes: ScheduleActivityTaskDecisionAttributes = None
    start_timer_decision_attributes: StartTimerDecisionAttributes = None
    complete_workflow_execution_decision_attributes: CompleteWorkflowExecutionDecisionAttributes = None
    fail_workflow_execution_decision_attributes: FailWorkflowExecutionDecisionAttributes = None
    request_cancel_activity_task_decision_attributes: RequestCancelActivityTaskDecisionAttributes = None
    cancel_timer_decision_attributes: CancelTimerDecisionAttributes = None
    cancel_workflow_execution_decision_attributes: CancelWorkflowExecutionDecisionAttributes = None
    request_cancel_external_workflow_execution_decision_attributes: RequestCancelExternalWorkflowExecutionDecisionAttributes = None
    record_marker_decision_attributes: RecordMarkerDecisionAttributes = None
    continue_as_new_workflow_execution_decision_attributes: ContinueAsNewWorkflowExecutionDecisionAttributes = None
    start_child_workflow_execution_decision_attributes: StartChildWorkflowExecutionDecisionAttributes = None
    signal_external_workflow_execution_decision_attributes: SignalExternalWorkflowExecutionDecisionAttributes = None
    upsert_workflow_search_attributes_decision_attributes: UpsertWorkflowSearchAttributesDecisionAttributes = None
    

# noinspection PyPep8
@dataclass
class WorkflowExecutionStartedEventAttributes:
    workflow_type: WorkflowType = None
    parent_workflow_domain: str = None
    parent_workflow_execution: WorkflowExecution = None
    parent_initiated_event_id: int = None
    task_list: TaskList = None
    input: bytes = None
    execution_start_to_close_timeout_seconds: int = None
    task_start_to_close_timeout_seconds: int = None
    child_policy: ChildPolicy = None
    continued_execution_run_id: str = None
    initiator: ContinueAsNewInitiator = None
    continued_failure_reason: str = None
    continued_failure_details: bytes = None
    last_completion_result: bytes = None
    original_execution_run_id: str = None
    identity: str = None
    first_execution_run_id: str = None
    retry_policy: RetryPolicy = None
    attempt: int = None
    expiration_timestamp: int = None
    cron_schedule: str = None
    first_decision_task_backoff_seconds: int = None
    memo: Memo = None
    search_attributes: SearchAttributes = None
    prev_auto_reset_points: ResetPoints = None
    header: Header = None
    

# noinspection PyPep8
@dataclass
class ResetPoints:
    points: List[ResetPointInfo] = field(default_factory=list)
    

# noinspection PyPep8
@dataclass
class ResetPointInfo:
    binary_checksum: str = None
    run_id: str = None
    first_decision_completed_id: int = None
    created_time_nano: int = None
    expiring_time_nano: int = None
    resettable: bool = None
    

# noinspection PyPep8
@dataclass
class WorkflowExecutionCompletedEventAttributes:
    result: bytes = None
    decision_task_completed_event_id: int = None
    

# noinspection PyPep8
@dataclass
class WorkflowExecutionFailedEventAttributes:
    reason: str = None
    details: bytes = None
    decision_task_completed_event_id: int = None
    

# noinspection PyPep8
@dataclass
class WorkflowExecutionTimedOutEventAttributes:
    timeout_type: TimeoutType = None
    

# noinspection PyPep8
@dataclass
class WorkflowExecutionContinuedAsNewEventAttributes:
    new_execution_run_id: str = None
    workflow_type: WorkflowType = None
    task_list: TaskList = None
    input: bytes = None
    execution_start_to_close_timeout_seconds: int = None
    task_start_to_close_timeout_seconds: int = None
    decision_task_completed_event_id: int = None
    backoff_start_interval_in_seconds: int = None
    initiator: ContinueAsNewInitiator = None
    failure_reason: str = None
    failure_details: bytes = None
    last_completion_result: bytes = None
    header: Header = None
    memo: Memo = None
    search_attributes: SearchAttributes = None
    

# noinspection PyPep8
@dataclass
class DecisionTaskScheduledEventAttributes:
    task_list: TaskList = None
    start_to_close_timeout_seconds: int = None
    attempt: int = None
    

# noinspection PyPep8
@dataclass
class DecisionTaskStartedEventAttributes:
    scheduled_event_id: int = None
    identity: str = None
    request_id: str = None
    

# noinspection PyPep8
@dataclass
class DecisionTaskCompletedEventAttributes:
    execution_context: bytes = None
    scheduled_event_id: int = None
    started_event_id: int = None
    identity: str = None
    binary_checksum: str = None
    

# noinspection PyPep8
@dataclass
class DecisionTaskTimedOutEventAttributes:
    scheduled_event_id: int = None
    started_event_id: int = None
    timeout_type: TimeoutType = None
    

# noinspection PyPep8
@dataclass
class DecisionTaskFailedEventAttributes:
    scheduled_event_id: int = None
    started_event_id: int = None
    cause: DecisionTaskFailedCause = None
    details: bytes = None
    identity: str = None
    reason: str = None
    base_run_id: str = None
    new_run_id: str = None
    fork_event_version: int = None
    

# noinspection PyPep8
@dataclass
class ActivityTaskScheduledEventAttributes:
    activity_id: str = None
    activity_type: ActivityType = None
    domain: str = None
    task_list: TaskList = None
    input: bytes = None
    schedule_to_close_timeout_seconds: int = None
    schedule_to_start_timeout_seconds: int = None
    start_to_close_timeout_seconds: int = None
    heartbeat_timeout_seconds: int = None
    decision_task_completed_event_id: int = None
    retry_policy: RetryPolicy = None
    header: Header = None
    

# noinspection PyPep8
@dataclass
class ActivityTaskStartedEventAttributes:
    scheduled_event_id: int = None
    identity: str = None
    request_id: str = None
    attempt: int = None
    

# noinspection PyPep8
@dataclass
class ActivityTaskCompletedEventAttributes:
    result: bytes = None
    scheduled_event_id: int = None
    started_event_id: int = None
    identity: str = None
    

# noinspection PyPep8
@dataclass
class ActivityTaskFailedEventAttributes:
    reason: str = None
    details: bytes = None
    scheduled_event_id: int = None
    started_event_id: int = None
    identity: str = None
    

# noinspection PyPep8
@dataclass
class ActivityTaskTimedOutEventAttributes:
    details: bytes = None
    scheduled_event_id: int = None
    started_event_id: int = None
    timeout_type: TimeoutType = None
    

# noinspection PyPep8
@dataclass
class ActivityTaskCancelRequestedEventAttributes:
    activity_id: str = None
    decision_task_completed_event_id: int = None
    

# noinspection PyPep8
@dataclass
class RequestCancelActivityTaskFailedEventAttributes:
    activity_id: str = None
    cause: str = None
    decision_task_completed_event_id: int = None
    

# noinspection PyPep8
@dataclass
class ActivityTaskCanceledEventAttributes:
    details: bytes = None
    latest_cancel_requested_event_id: int = None
    scheduled_event_id: int = None
    started_event_id: int = None
    identity: str = None
    

# noinspection PyPep8
@dataclass
class TimerStartedEventAttributes:
    timer_id: str = None
    start_to_fire_timeout_seconds: int = None
    decision_task_completed_event_id: int = None
    

# noinspection PyPep8
@dataclass
class TimerFiredEventAttributes:
    timer_id: str = None
    started_event_id: int = None
    

# noinspection PyPep8
@dataclass
class TimerCanceledEventAttributes:
    timer_id: str = None
    started_event_id: int = None
    decision_task_completed_event_id: int = None
    identity: str = None
    

# noinspection PyPep8
@dataclass
class CancelTimerFailedEventAttributes:
    timer_id: str = None
    cause: str = None
    decision_task_completed_event_id: int = None
    identity: str = None
    

# noinspection PyPep8
@dataclass
class WorkflowExecutionCancelRequestedEventAttributes:
    cause: str = None
    external_initiated_event_id: int = None
    external_workflow_execution: WorkflowExecution = None
    identity: str = None
    

# noinspection PyPep8
@dataclass
class WorkflowExecutionCanceledEventAttributes:
    decision_task_completed_event_id: int = None
    details: bytes = None
    

# noinspection PyPep8
@dataclass
class MarkerRecordedEventAttributes:
    marker_name: str = None
    details: bytes = None
    decision_task_completed_event_id: int = None
    header: Header = None
    

# noinspection PyPep8
@dataclass
class WorkflowExecutionSignaledEventAttributes:
    signal_name: str = None
    input: bytes = None
    identity: str = None
    

# noinspection PyPep8
@dataclass
class WorkflowExecutionTerminatedEventAttributes:
    reason: str = None
    details: bytes = None
    identity: str = None
    

# noinspection PyPep8
@dataclass
class RequestCancelExternalWorkflowExecutionInitiatedEventAttributes:
    decision_task_completed_event_id: int = None
    domain: str = None
    workflow_execution: WorkflowExecution = None
    control: bytes = None
    child_workflow_only: bool = None
    

# noinspection PyPep8
@dataclass
class RequestCancelExternalWorkflowExecutionFailedEventAttributes:
    cause: CancelExternalWorkflowExecutionFailedCause = None
    decision_task_completed_event_id: int = None
    domain: str = None
    workflow_execution: WorkflowExecution = None
    initiated_event_id: int = None
    control: bytes = None
    

# noinspection PyPep8
@dataclass
class ExternalWorkflowExecutionCancelRequestedEventAttributes:
    initiated_event_id: int = None
    domain: str = None
    workflow_execution: WorkflowExecution = None
    

# noinspection PyPep8
@dataclass
class SignalExternalWorkflowExecutionInitiatedEventAttributes:
    decision_task_completed_event_id: int = None
    domain: str = None
    workflow_execution: WorkflowExecution = None
    signal_name: str = None
    input: bytes = None
    control: bytes = None
    child_workflow_only: bool = None
    

# noinspection PyPep8
@dataclass
class SignalExternalWorkflowExecutionFailedEventAttributes:
    cause: SignalExternalWorkflowExecutionFailedCause = None
    decision_task_completed_event_id: int = None
    domain: str = None
    workflow_execution: WorkflowExecution = None
    initiated_event_id: int = None
    control: bytes = None
    

# noinspection PyPep8
@dataclass
class ExternalWorkflowExecutionSignaledEventAttributes:
    initiated_event_id: int = None
    domain: str = None
    workflow_execution: WorkflowExecution = None
    control: bytes = None
    

# noinspection PyPep8
@dataclass
class UpsertWorkflowSearchAttributesEventAttributes:
    decision_task_completed_event_id: int = None
    search_attributes: SearchAttributes = None
    

# noinspection PyPep8
@dataclass
class StartChildWorkflowExecutionInitiatedEventAttributes:
    domain: str = None
    workflow_id: str = None
    workflow_type: WorkflowType = None
    task_list: TaskList = None
    input: bytes = None
    execution_start_to_close_timeout_seconds: int = None
    task_start_to_close_timeout_seconds: int = None
    child_policy: ChildPolicy = None
    control: bytes = None
    decision_task_completed_event_id: int = None
    workflow_id_reuse_policy: WorkflowIdReusePolicy = None
    retry_policy: RetryPolicy = None
    cron_schedule: str = None
    header: Header = None
    memo: Memo = None
    search_attributes: SearchAttributes = None
    

# noinspection PyPep8
@dataclass
class StartChildWorkflowExecutionFailedEventAttributes:
    domain: str = None
    workflow_id: str = None
    workflow_type: WorkflowType = None
    cause: ChildWorkflowExecutionFailedCause = None
    control: bytes = None
    initiated_event_id: int = None
    decision_task_completed_event_id: int = None
    

# noinspection PyPep8
@dataclass
class ChildWorkflowExecutionStartedEventAttributes:
    domain: str = None
    initiated_event_id: int = None
    workflow_execution: WorkflowExecution = None
    workflow_type: WorkflowType = None
    header: Header = None
    

# noinspection PyPep8
@dataclass
class ChildWorkflowExecutionCompletedEventAttributes:
    result: bytes = None
    domain: str = None
    workflow_execution: WorkflowExecution = None
    workflow_type: WorkflowType = None
    initiated_event_id: int = None
    started_event_id: int = None
    

# noinspection PyPep8
@dataclass
class ChildWorkflowExecutionFailedEventAttributes:
    reason: str = None
    details: bytes = None
    domain: str = None
    workflow_execution: WorkflowExecution = None
    workflow_type: WorkflowType = None
    initiated_event_id: int = None
    started_event_id: int = None
    

# noinspection PyPep8
@dataclass
class ChildWorkflowExecutionCanceledEventAttributes:
    details: bytes = None
    domain: str = None
    workflow_execution: WorkflowExecution = None
    workflow_type: WorkflowType = None
    initiated_event_id: int = None
    started_event_id: int = None
    

# noinspection PyPep8
@dataclass
class ChildWorkflowExecutionTimedOutEventAttributes:
    timeout_type: TimeoutType = None
    domain: str = None
    workflow_execution: WorkflowExecution = None
    workflow_type: WorkflowType = None
    initiated_event_id: int = None
    started_event_id: int = None
    

# noinspection PyPep8
@dataclass
class ChildWorkflowExecutionTerminatedEventAttributes:
    domain: str = None
    workflow_execution: WorkflowExecution = None
    workflow_type: WorkflowType = None
    initiated_event_id: int = None
    started_event_id: int = None
    

# noinspection PyPep8
@dataclass
class HistoryEvent:
    event_id: int = None
    timestamp: int = None
    event_type: EventType = None
    version: int = None
    task_id: int = None
    workflow_execution_started_event_attributes: WorkflowExecutionStartedEventAttributes = None
    workflow_execution_completed_event_attributes: WorkflowExecutionCompletedEventAttributes = None
    workflow_execution_failed_event_attributes: WorkflowExecutionFailedEventAttributes = None
    workflow_execution_timed_out_event_attributes: WorkflowExecutionTimedOutEventAttributes = None
    decision_task_scheduled_event_attributes: DecisionTaskScheduledEventAttributes = None
    decision_task_started_event_attributes: DecisionTaskStartedEventAttributes = None
    decision_task_completed_event_attributes: DecisionTaskCompletedEventAttributes = None
    decision_task_timed_out_event_attributes: DecisionTaskTimedOutEventAttributes = None
    decision_task_failed_event_attributes: DecisionTaskFailedEventAttributes = None
    activity_task_scheduled_event_attributes: ActivityTaskScheduledEventAttributes = None
    activity_task_started_event_attributes: ActivityTaskStartedEventAttributes = None
    activity_task_completed_event_attributes: ActivityTaskCompletedEventAttributes = None
    activity_task_failed_event_attributes: ActivityTaskFailedEventAttributes = None
    activity_task_timed_out_event_attributes: ActivityTaskTimedOutEventAttributes = None
    timer_started_event_attributes: TimerStartedEventAttributes = None
    timer_fired_event_attributes: TimerFiredEventAttributes = None
    activity_task_cancel_requested_event_attributes: ActivityTaskCancelRequestedEventAttributes = None
    request_cancel_activity_task_failed_event_attributes: RequestCancelActivityTaskFailedEventAttributes = None
    activity_task_canceled_event_attributes: ActivityTaskCanceledEventAttributes = None
    timer_canceled_event_attributes: TimerCanceledEventAttributes = None
    cancel_timer_failed_event_attributes: CancelTimerFailedEventAttributes = None
    marker_recorded_event_attributes: MarkerRecordedEventAttributes = None
    workflow_execution_signaled_event_attributes: WorkflowExecutionSignaledEventAttributes = None
    workflow_execution_terminated_event_attributes: WorkflowExecutionTerminatedEventAttributes = None
    workflow_execution_cancel_requested_event_attributes: WorkflowExecutionCancelRequestedEventAttributes = None
    workflow_execution_canceled_event_attributes: WorkflowExecutionCanceledEventAttributes = None
    request_cancel_external_workflow_execution_initiated_event_attributes: RequestCancelExternalWorkflowExecutionInitiatedEventAttributes = None
    request_cancel_external_workflow_execution_failed_event_attributes: RequestCancelExternalWorkflowExecutionFailedEventAttributes = None
    external_workflow_execution_cancel_requested_event_attributes: ExternalWorkflowExecutionCancelRequestedEventAttributes = None
    workflow_execution_continued_as_new_event_attributes: WorkflowExecutionContinuedAsNewEventAttributes = None
    start_child_workflow_execution_initiated_event_attributes: StartChildWorkflowExecutionInitiatedEventAttributes = None
    start_child_workflow_execution_failed_event_attributes: StartChildWorkflowExecutionFailedEventAttributes = None
    child_workflow_execution_started_event_attributes: ChildWorkflowExecutionStartedEventAttributes = None
    child_workflow_execution_completed_event_attributes: ChildWorkflowExecutionCompletedEventAttributes = None
    child_workflow_execution_failed_event_attributes: ChildWorkflowExecutionFailedEventAttributes = None
    child_workflow_execution_canceled_event_attributes: ChildWorkflowExecutionCanceledEventAttributes = None
    child_workflow_execution_timed_out_event_attributes: ChildWorkflowExecutionTimedOutEventAttributes = None
    child_workflow_execution_terminated_event_attributes: ChildWorkflowExecutionTerminatedEventAttributes = None
    signal_external_workflow_execution_initiated_event_attributes: SignalExternalWorkflowExecutionInitiatedEventAttributes = None
    signal_external_workflow_execution_failed_event_attributes: SignalExternalWorkflowExecutionFailedEventAttributes = None
    external_workflow_execution_signaled_event_attributes: ExternalWorkflowExecutionSignaledEventAttributes = None
    upsert_workflow_search_attributes_event_attributes: UpsertWorkflowSearchAttributesEventAttributes = None
    

# noinspection PyPep8
@dataclass
class History:
    events: List[HistoryEvent] = field(default_factory=list)
    

# noinspection PyPep8
@dataclass
class WorkflowExecutionFilter:
    workflow_id: str = None
    

# noinspection PyPep8
@dataclass
class WorkflowTypeFilter:
    name: str = None
    

# noinspection PyPep8
@dataclass
class StartTimeFilter:
    earliest_time: int = None
    latest_time: int = None
    

# noinspection PyPep8
@dataclass
class DomainInfo:
    name: str = None
    status: DomainStatus = None
    description: str = None
    owner_email: str = None
    data: Dict[str, str] = field(default_factory=dict)
    uuid: str = None
    

# noinspection PyPep8
@dataclass
class DomainConfiguration:
    workflow_execution_retention_period_in_days: int = None
    emit_metric: bool = None
    archival_bucket_name: str = None
    archival_status: ArchivalStatus = None
    bad_binaries: BadBinaries = None
    

# noinspection PyPep8
@dataclass
class BadBinaries:
    binaries: Dict[str, BadBinaryInfo] = field(default_factory=dict)
    

# noinspection PyPep8
@dataclass
class BadBinaryInfo:
    reason: str = None
    operator: str = None
    created_time_nano: int = None
    

# noinspection PyPep8
@dataclass
class UpdateDomainInfo:
    description: str = None
    owner_email: str = None
    data: Dict[str, str] = field(default_factory=dict)
    

# noinspection PyPep8
@dataclass
class ClusterReplicationConfiguration:
    cluster_name: str = None
    

# noinspection PyPep8
@dataclass
class DomainReplicationConfiguration:
    active_cluster_name: str = None
    clusters: List[ClusterReplicationConfiguration] = field(default_factory=list)
    

# noinspection PyPep8
@dataclass
class RegisterDomainRequest:
    name: str = None
    description: str = None
    owner_email: str = None
    workflow_execution_retention_period_in_days: int = None
    emit_metric: bool = None
    clusters: List[ClusterReplicationConfiguration] = field(default_factory=list)
    active_cluster_name: str = None
    data: Dict[str, str] = field(default_factory=dict)
    security_token: str = None
    archival_status: ArchivalStatus = None
    archival_bucket_name: str = None
    is_global_domain: bool = None
    

# noinspection PyPep8
@dataclass
class ListDomainsRequest:
    page_size: int = None
    next_page_token: bytes = None
    

# noinspection PyPep8
@dataclass
class ListDomainsResponse:
    domains: List[DescribeDomainResponse] = field(default_factory=list)
    next_page_token: bytes = None
    

# noinspection PyPep8
@dataclass
class DescribeDomainRequest:
    name: str = None
    uuid: str = None
    

# noinspection PyPep8
@dataclass
class DescribeDomainResponse:
    domain_info: DomainInfo = None
    configuration: DomainConfiguration = None
    replication_configuration: DomainReplicationConfiguration = None
    failover_version: int = None
    is_global_domain: bool = None
    

# noinspection PyPep8
@dataclass
class UpdateDomainRequest:
    name: str = None
    updated_info: UpdateDomainInfo = None
    configuration: DomainConfiguration = None
    replication_configuration: DomainReplicationConfiguration = None
    security_token: str = None
    delete_bad_binary: str = None
    

# noinspection PyPep8
@dataclass
class UpdateDomainResponse:
    domain_info: DomainInfo = None
    configuration: DomainConfiguration = None
    replication_configuration: DomainReplicationConfiguration = None
    failover_version: int = None
    is_global_domain: bool = None
    

# noinspection PyPep8
@dataclass
class DeprecateDomainRequest:
    name: str = None
    security_token: str = None
    

# noinspection PyPep8
@dataclass
class StartWorkflowExecutionRequest:
    domain: str = None
    workflow_id: str = None
    workflow_type: WorkflowType = None
    task_list: TaskList = None
    input: bytes = None
    execution_start_to_close_timeout_seconds: int = None
    task_start_to_close_timeout_seconds: int = None
    identity: str = None
    request_id: str = None
    workflow_id_reuse_policy: WorkflowIdReusePolicy = None
    child_policy: ChildPolicy = None
    retry_policy: RetryPolicy = None
    cron_schedule: str = None
    memo: Memo = None
    search_attributes: SearchAttributes = None
    header: Header = None
    

# noinspection PyPep8
@dataclass
class StartWorkflowExecutionResponse:
    run_id: str = None
    

# noinspection PyPep8
@dataclass
class PollForDecisionTaskRequest:
    domain: str = None
    task_list: TaskList = None
    identity: str = None
    binary_checksum: str = None
    

# noinspection PyPep8
@dataclass
class PollForDecisionTaskResponse:
    task_token: bytes = None
    workflow_execution: WorkflowExecution = None
    workflow_type: WorkflowType = None
    previous_started_event_id: int = None
    started_event_id: int = None
    attempt: int = None
    backlog_count_hint: int = None
    history: History = None
    next_page_token: bytes = None
    query: WorkflowQuery = None
    workflow_execution_task_list: TaskList = None
    scheduled_timestamp: int = None
    started_timestamp: int = None
    

# noinspection PyPep8
@dataclass
class StickyExecutionAttributes:
    worker_task_list: TaskList = None
    schedule_to_start_timeout_seconds: int = None
    

# noinspection PyPep8
@dataclass
class RespondDecisionTaskCompletedRequest:
    task_token: bytes = None
    decisions: List[Decision] = field(default_factory=list)
    execution_context: bytes = None
    identity: str = None
    sticky_attributes: StickyExecutionAttributes = None
    return_new_decision_task: bool = None
    force_create_new_decision_task: bool = None
    binary_checksum: str = None
    

# noinspection PyPep8
@dataclass
class RespondDecisionTaskCompletedResponse:
    decision_task: PollForDecisionTaskResponse = None
    

# noinspection PyPep8
@dataclass
class RespondDecisionTaskFailedRequest:
    task_token: bytes = None
    cause: DecisionTaskFailedCause = None
    details: bytes = None
    identity: str = None
    

# noinspection PyPep8
@dataclass
class PollForActivityTaskRequest:
    domain: str = None
    task_list: TaskList = None
    identity: str = None
    task_list_metadata: TaskListMetadata = None
    

# noinspection PyPep8
@dataclass
class PollForActivityTaskResponse:
    task_token: bytes = None
    workflow_execution: WorkflowExecution = None
    activity_id: str = None
    activity_type: ActivityType = None
    input: bytes = None
    scheduled_timestamp: int = None
    schedule_to_close_timeout_seconds: int = None
    started_timestamp: int = None
    start_to_close_timeout_seconds: int = None
    heartbeat_timeout_seconds: int = None
    attempt: int = None
    scheduled_timestamp_of_this_attempt: int = None
    heartbeat_details: bytes = None
    workflow_type: WorkflowType = None
    workflow_domain: str = None
    header: Header = None
    

# noinspection PyPep8
@dataclass
class RecordActivityTaskHeartbeatRequest:
    task_token: bytes = None
    details: bytes = None
    identity: str = None
    

# noinspection PyPep8
@dataclass
class RecordActivityTaskHeartbeatByIDRequest:
    domain: str = None
    workflow_id: str = None
    run_id: str = None
    activity_id: str = None
    details: bytes = None
    identity: str = None
    

# noinspection PyPep8
@dataclass
class RecordActivityTaskHeartbeatResponse:
    cancel_requested: bool = None
    

# noinspection PyPep8
@dataclass
class RespondActivityTaskCompletedRequest:
    task_token: bytes = None
    result: bytes = None
    identity: str = None
    

# noinspection PyPep8
@dataclass
class RespondActivityTaskFailedRequest:
    task_token: bytes = None
    reason: str = None
    details: bytes = None
    identity: str = None
    

# noinspection PyPep8
@dataclass
class RespondActivityTaskCanceledRequest:
    task_token: bytes = None
    details: bytes = None
    identity: str = None
    

# noinspection PyPep8
@dataclass
class RespondActivityTaskCompletedByIDRequest:
    domain: str = None
    workflow_id: str = None
    run_id: str = None
    activity_id: str = None
    result: bytes = None
    identity: str = None
    

# noinspection PyPep8
@dataclass
class RespondActivityTaskFailedByIDRequest:
    domain: str = None
    workflow_id: str = None
    run_id: str = None
    activity_id: str = None
    reason: str = None
    details: bytes = None
    identity: str = None
    

# noinspection PyPep8
@dataclass
class RespondActivityTaskCanceledByIDRequest:
    domain: str = None
    workflow_id: str = None
    run_id: str = None
    activity_id: str = None
    details: bytes = None
    identity: str = None
    

# noinspection PyPep8
@dataclass
class RequestCancelWorkflowExecutionRequest:
    domain: str = None
    workflow_execution: WorkflowExecution = None
    identity: str = None
    request_id: str = None
    

# noinspection PyPep8
@dataclass
class GetWorkflowExecutionHistoryRequest:
    domain: str = None
    execution: WorkflowExecution = None
    maximum_page_size: int = None
    next_page_token: bytes = None
    wait_for_new_event: bool = None
    history_event_filter_type: HistoryEventFilterType = None
    

# noinspection PyPep8
@dataclass
class GetWorkflowExecutionHistoryResponse:
    history: History = None
    next_page_token: bytes = None
    archived: bool = None
    

# noinspection PyPep8
@dataclass
class SignalWorkflowExecutionRequest:
    domain: str = None
    workflow_execution: WorkflowExecution = None
    signal_name: str = None
    input: bytes = None
    identity: str = None
    request_id: str = None
    control: bytes = None
    

# noinspection PyPep8
@dataclass
class SignalWithStartWorkflowExecutionRequest:
    domain: str = None
    workflow_id: str = None
    workflow_type: WorkflowType = None
    task_list: TaskList = None
    input: bytes = None
    execution_start_to_close_timeout_seconds: int = None
    task_start_to_close_timeout_seconds: int = None
    identity: str = None
    request_id: str = None
    workflow_id_reuse_policy: WorkflowIdReusePolicy = None
    signal_name: str = None
    signal_input: bytes = None
    control: bytes = None
    retry_policy: RetryPolicy = None
    cron_schedule: str = None
    memo: Memo = None
    search_attributes: SearchAttributes = None
    header: Header = None
    

# noinspection PyPep8
@dataclass
class TerminateWorkflowExecutionRequest:
    domain: str = None
    workflow_execution: WorkflowExecution = None
    reason: str = None
    details: bytes = None
    identity: str = None
    

# noinspection PyPep8
@dataclass
class ResetWorkflowExecutionRequest:
    domain: str = None
    workflow_execution: WorkflowExecution = None
    reason: str = None
    decision_finish_event_id: int = None
    request_id: str = None
    

# noinspection PyPep8
@dataclass
class ResetWorkflowExecutionResponse:
    run_id: str = None
    

# noinspection PyPep8
@dataclass
class ListOpenWorkflowExecutionsRequest:
    domain: str = None
    maximum_page_size: int = None
    next_page_token: bytes = None
    start_time_filter: StartTimeFilter = None
    execution_filter: WorkflowExecutionFilter = None
    type_filter: WorkflowTypeFilter = None
    

# noinspection PyPep8
@dataclass
class ListOpenWorkflowExecutionsResponse:
    executions: List[WorkflowExecutionInfo] = field(default_factory=list)
    next_page_token: bytes = None
    

# noinspection PyPep8
@dataclass
class ListClosedWorkflowExecutionsRequest:
    domain: str = None
    maximum_page_size: int = None
    next_page_token: bytes = None
    start_time_filter: StartTimeFilter = None
    execution_filter: WorkflowExecutionFilter = None
    type_filter: WorkflowTypeFilter = None
    status_filter: WorkflowExecutionCloseStatus = None
    

# noinspection PyPep8
@dataclass
class ListClosedWorkflowExecutionsResponse:
    executions: List[WorkflowExecutionInfo] = field(default_factory=list)
    next_page_token: bytes = None
    

# noinspection PyPep8
@dataclass
class ListWorkflowExecutionsRequest:
    domain: str = None
    page_size: int = None
    next_page_token: bytes = None
    query: str = None
    

# noinspection PyPep8
@dataclass
class ListWorkflowExecutionsResponse:
    executions: List[WorkflowExecutionInfo] = field(default_factory=list)
    next_page_token: bytes = None
    

# noinspection PyPep8
@dataclass
class CountWorkflowExecutionsRequest:
    domain: str = None
    query: str = None
    

# noinspection PyPep8
@dataclass
class CountWorkflowExecutionsResponse:
    count: int = None
    

# noinspection PyPep8
@dataclass
class GetSearchAttributesResponse:
    keys: Dict[str, IndexedValueType] = field(default_factory=dict)
    

# noinspection PyPep8
@dataclass
class QueryWorkflowRequest:
    domain: str = None
    execution: WorkflowExecution = None
    query: WorkflowQuery = None
    query_reject_condition: QueryRejectCondition = None
    

# noinspection PyPep8
@dataclass
class QueryRejected:
    close_status: WorkflowExecutionCloseStatus = None
    

# noinspection PyPep8
@dataclass
class QueryWorkflowResponse:
    query_result: bytes = None
    query_rejected: QueryRejected = None
    

# noinspection PyPep8
@dataclass
class WorkflowQuery:
    query_type: str = None
    query_args: bytes = None
    

# noinspection PyPep8
@dataclass
class ResetStickyTaskListRequest:
    domain: str = None
    execution: WorkflowExecution = None
    

# noinspection PyPep8
@dataclass
class ResetStickyTaskListResponse:
    pass
    

# noinspection PyPep8
@dataclass
class RespondQueryTaskCompletedRequest:
    task_token: bytes = None
    completed_type: QueryTaskCompletedType = None
    query_result: bytes = None
    error_message: str = None
    

# noinspection PyPep8
@dataclass
class DescribeWorkflowExecutionRequest:
    domain: str = None
    execution: WorkflowExecution = None
    

# noinspection PyPep8
@dataclass
class PendingActivityInfo:
    activity_id: str = None
    activity_type: ActivityType = None
    state: PendingActivityState = None
    heartbeat_details: bytes = None
    last_heartbeat_timestamp: int = None
    last_started_timestamp: int = None
    attempt: int = None
    maximum_attempts: int = None
    scheduled_timestamp: int = None
    expiration_timestamp: int = None
    last_failure_reason: str = None
    last_worker_identity: str = None
    

# noinspection PyPep8
@dataclass
class PendingChildExecutionInfo:
    workflow_id: str = None
    run_id: str = None
    workflow_typ_name: str = None
    initiated_id: int = None
    

# noinspection PyPep8
@dataclass
class DescribeWorkflowExecutionResponse:
    execution_configuration: WorkflowExecutionConfiguration = None
    workflow_execution_info: WorkflowExecutionInfo = None
    pending_activities: List[PendingActivityInfo] = field(default_factory=list)
    pending_children: List[PendingChildExecutionInfo] = field(default_factory=list)
    

# noinspection PyPep8
@dataclass
class DescribeTaskListRequest:
    domain: str = None
    task_list: TaskList = None
    task_list_type: TaskListType = None
    include_task_list_status: bool = None
    

# noinspection PyPep8
@dataclass
class DescribeTaskListResponse:
    pollers: List[PollerInfo] = field(default_factory=list)
    task_list_status: TaskListStatus = None
    

# noinspection PyPep8
@dataclass
class TaskListStatus:
    backlog_count_hint: int = None
    read_level: int = None
    ack_level: int = None
    rate_per_second: float = None
    task_id_block: TaskIDBlock = None
    

# noinspection PyPep8
@dataclass
class TaskIDBlock:
    start_id: int = None
    end_id: int = None
    

# noinspection PyPep8
@dataclass
class DescribeHistoryHostRequest:
    host_address: str = None
    shard_id_for_host: int = None
    execution_for_host: WorkflowExecution = None
    

# noinspection PyPep8
@dataclass
class DescribeHistoryHostResponse:
    number_of_shards: int = None
    shard_i_ds: List[int] = field(default_factory=list)
    domain_cache: DomainCacheInfo = None
    shard_controller_status: str = None
    address: str = None
    

# noinspection PyPep8
@dataclass
class DomainCacheInfo:
    num_of_items_in_cache_by_id: int = None
    num_of_items_in_cache_by_name: int = None
    

# noinspection PyPep8
@dataclass
class PollerInfo:
    last_access_time: int = None
    identity: str = None
    rate_per_second: float = None
    

# noinspection PyPep8
@dataclass
class RetryPolicy:
    initial_interval_in_seconds: int = None
    backoff_coefficient: float = None
    maximum_interval_in_seconds: int = None
    maximum_attempts: int = None
    non_retriable_error_reasons: List[str] = field(default_factory=list)
    expiration_interval_in_seconds: int = None
    

# noinspection PyPep8
@dataclass
class HistoryBranchRange:
    branch_id: str = None
    begin_node_id: int = None
    end_node_id: int = None
    

# noinspection PyPep8
@dataclass
class HistoryBranch:
    tree_id: str = None
    branch_id: str = None
    ancestors: List[HistoryBranchRange] = field(default_factory=list)
