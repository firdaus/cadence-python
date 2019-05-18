import sys

from cadence.cadence_types import RegisterDomainRequest
from cadence.workflowservice import WorkflowService

if __name__ == "__main__":
    service = WorkflowService.create("localhost", 7933)

    domain = sys.argv[1]

    register_domain_request = RegisterDomainRequest()
    register_domain_request.name = "test-domain"
    register_domain_request.workflow_execution_retention_period_in_days = 1

    _, err = service.register_domain(register_domain_request)
    if err:
        print(err)
    else:
        print(f"Registered domain f{domain}")
