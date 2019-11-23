import contextvars
from dataclasses import dataclass

from cadence.cadence_types import WorkflowExecution

current_activity_context = contextvars.ContextVar("current_activity_context")


@dataclass
class ActivityContext:
    task_token: bytes = None
    workflow_execution: WorkflowExecution = None
    domain: str = None

    @staticmethod
    def get() -> 'ActivityContext':
        return current_activity_context.get()

    @staticmethod
    def set(context: 'ActivityContext'):
        current_activity_context.set(context)


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
