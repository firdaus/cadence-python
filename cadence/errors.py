from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class BadRequestError:
    message: str


@dataclass
class InternalServiceError:
    message: str


@dataclass
class DomainAlreadyExistsError:
    message: str


@dataclass
class WorkflowExecutionAlreadyStartedError:
    message: Optional[str]
    startRequestId: Optional[str]
    runId: Optional[str]

    @property
    def start_request_id(self):
        return self.startRequestId

    @property
    def run_id(self):
        return self.runId


@dataclass
class EntityNotExistsError:
    message: str


@dataclass
class ServiceBusyError:
    message: str


@dataclass
class CancellationAlreadyRequestedError:
    message: str


@dataclass
class QueryFailedError:
    message: str


@dataclass
class DomainNotActiveError:
    message: str
    domainName: str
    currentCluster: str
    activeCluster: str

    @property
    def domain_name(self):
        return self.domainName

    @property
    def current_cluster(self):
        return self.currentCluster

    @property
    def active_cluster(self):
        return self.activeCluster


@dataclass
class LimitExceededError:
    message: str


@dataclass
class AccessDeniedError:
    message: str


@dataclass
class RetryTaskError:
    message: str
    domain_id: str
    workflow_id: str
    run_id: str
    next_event_id: int


@dataclass
class ClientVersionNotSupportedError:
    feature_version: str
    client_impl: str
    supported_versions: str


CADENCE_ERROR_FIELDS = {
    "badRequestError": BadRequestError,
    "internalServiceError": InternalServiceError,
    "domainExistsError": DomainAlreadyExistsError,
    "sessionAlreadyExistError": WorkflowExecutionAlreadyStartedError,
    "entityNotExistError": EntityNotExistsError,
    "serviceBusyError": ServiceBusyError,
    "cancellationAlreadyRequestedError": CancellationAlreadyRequestedError,
    "queryFailedError": QueryFailedError,
    "domainNotActiveError": DomainNotActiveError,
    "limitExceededError": LimitExceededError,
    "workflowAlreadyStartedError": WorkflowExecutionAlreadyStartedError,
    "clientVersionNotSupportedError": ClientVersionNotSupportedError
}

IGNORE_FIELDS_IN_ERRORS = ("args", "type_spec", "from_primitive", "to_primitive", "with_traceback")


def find_error(response):
    for key, cls in CADENCE_ERROR_FIELDS.items():
        error = getattr(response, key, None)
        if error:
            kwargs = {}
            for field in dir(error):
                if field not in IGNORE_FIELDS_IN_ERRORS and not field.startswith("__"):
                    kwargs[field] = getattr(error, field)
            return cls(**kwargs)
    return None
