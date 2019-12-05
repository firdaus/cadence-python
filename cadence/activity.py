import contextvars
import json
from dataclasses import dataclass

from cadence.cadence_types import WorkflowExecution, RecordActivityTaskHeartbeatRequest, ActivityType, \
    PollForActivityTaskResponse
from cadence.exceptions import ActivityCancelledException
from cadence.workflowservice import WorkflowService

current_activity_context = contextvars.ContextVar("current_activity_context")


@dataclass
class ActivityTask:
    @classmethod
    def from_poll_for_activity_task_response(cls, task: PollForActivityTaskResponse) -> 'ActivityTask':
        activity_task: 'ActivityTask' = cls()
        activity_task.task_token = task.task_token
        activity_task.workflow_execution = task.workflow_execution
        activity_task.activity_id = task.activity_id
        activity_task.activity_type = task.activity_type
        activity_task.scheduled_timestamp = task.scheduled_timestamp
        activity_task.schedule_to_close_timeout_seconds = task.schedule_to_close_timeout_seconds
        activity_task.start_to_close_timeout_seconds = task.start_to_close_timeout_seconds
        activity_task.heartbeat_timeout_seconds = task.heartbeat_timeout_seconds
        activity_task.attempt = task.attempt
        activity_task.heartbeat_details = task.heartbeat_details
        activity_task.workflow_domain = task.workflow_domain
        return activity_task

    task_token: bytes = None
    workflow_execution: WorkflowExecution = None
    activity_id: str = None
    activity_type: ActivityType = None
    scheduled_timestamp: int = None
    schedule_to_close_timeout_seconds: int = None
    start_to_close_timeout_seconds: int = None
    heartbeat_timeout_seconds: int = None
    attempt: int = None
    heartbeat_details: bytes = None
    workflow_domain: str = None


def heartbeat(service: WorkflowService, task_token: bytes, details: object):
    request = RecordActivityTaskHeartbeatRequest()
    request.details = json.dumps(details).encode("utf-8")
    request.identity = WorkflowService.get_identity()
    request.task_token = task_token
    response, error = service.record_activity_task_heartbeat(request)
    if error:
        raise error
    if response.cancel_requested:
        raise ActivityCancelledException()


def get_heartbeat_details(heartbeat_details) -> object:
    if not heartbeat_details:
        return None
    json_text = heartbeat_details.decode("utf-8")
    return json.loads(json_text)


class ActivityContext:
    service: WorkflowService = None
    activity_task: ActivityTask = None
    domain: str = None

    @staticmethod
    def get() -> 'ActivityContext':
        return current_activity_context.get()

    @staticmethod
    def set(context: 'ActivityContext'):
        current_activity_context.set(context)

    def heartbeat(self, details: object):
        heartbeat(self.service, self.activity_task.task_token, details)

    def get_heartbeat_details(self) -> object:
        return get_heartbeat_details(self.activity_task.heartbeat_details)


class Activity:

    @staticmethod
    def get_task_token() -> bytes:
        return ActivityContext.get().activity_task.task_token

    @staticmethod
    def get_workflow_execution() -> WorkflowExecution:
        return ActivityContext.get().activity_task.workflow_execution

    @staticmethod
    def get_domain() -> str:
        return ActivityContext.get().domain

    @staticmethod
    def get_heartbeat_details() -> object:
        return ActivityContext.get().get_heartbeat_details()

    @staticmethod
    def heartbeat(details: object):
        ActivityContext.get().heartbeat(details)
