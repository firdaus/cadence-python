from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class DecisionState(Enum):
    CREATED = 1
    DECISION_SENT = 2
    CANCELED_BEFORE_INITIATED = 3
    INITIATED = 4
    STARTED = 5
    CANCELED_AFTER_INITIATED = 6
    CANCELED_AFTER_STARTED = 7
    CANCELLATION_DECISION_SENT = 8
    COMPLETED_AFTER_CANCELLATION_DECISION_SENT = 9
    COMPLETED = 10


class DecisionTarget(Enum):
    ACTIVITY = 1
    CHILD_WORKFLOW = 2
    CANCEL_EXTERNAL_WORKFLOW = 3
    SIGNAL_EXTERNAL_WORKFLOW = 4
    TIMER = 5
    MARKER = 6

    # Probably won't end up using this since the Python version won't have something analagous to
    # CompleteWorkflowStateMachine
    SELF = 7


@dataclass
class DecisionId:
    decision_target: DecisionTarget
    decision_event_id: int

    def __str__(self):
        return f"{self.decision_target}:{self.decision_event_id}"

    def __hash__(self):
        return hash(self.__str__())

    def __eq__(self, other: DecisionId):
        return (self.decision_target == other.decision_target) and (self.decision_event_id == other.decision_event_id)
