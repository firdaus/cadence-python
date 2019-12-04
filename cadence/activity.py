import contextvars
import json
from dataclasses import dataclass

from cadence.cadence_types import WorkflowExecution, RecordActivityTaskHeartbeatRequest
from cadence.exceptions import ActivityCancelledException
from cadence.workflowservice import WorkflowService

current_activity_context = contextvars.ContextVar("current_activity_context")


@dataclass
class ActivityContext:
    task_token: bytes = None
    workflow_execution: WorkflowExecution = None
    domain: str = None
    service: WorkflowService = None

    @staticmethod
    def get() -> 'ActivityContext':
        return current_activity_context.get()

    @staticmethod
    def set(context: 'ActivityContext'):
        current_activity_context.set(context)

    def heartbeat(self, details: object):
        request = RecordActivityTaskHeartbeatRequest()
        request.details = json.dumps(details)
        request.identity = WorkflowService.get_identity()
        request.task_token = self.task_token
        response, error = self.service.record_activity_task_heartbeat(request)
        if error:
            raise error
        if response.cancel_requested:
            raise ActivityCancelledException()


class Activity:

    @staticmethod
    def get_task_token() -> bytes:
        return ActivityContext.get().task_token

    @staticmethod
    def get_workflow_execution() -> WorkflowExecution:
        return ActivityContext.get().workflow_execution

    @staticmethod
    def get_domain() -> str:
        return ActivityContext.get().domain

    @staticmethod
    def heartbeat(details: object):
        ActivityContext.get().heartbeat(details)
