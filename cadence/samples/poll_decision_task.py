import dataclasses
import json

from cadence.cadence_types import GetWorkflowExecutionHistoryRequest, WorkflowExecution, PollForDecisionTaskRequest, \
    TaskList
from cadence.workflowservice import WorkflowService


class Encoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        if isinstance(o, bytes):
            return str(o, 'utf-8')
        return super().default(o)


if __name__ == "__main__":
    service = WorkflowService.create("localhost", 7933)

    while True:
        poll_request = PollForDecisionTaskRequest()
        poll_request.domain = "sample"
        poll_request.identity = service.get_identity()
        poll_request.task_list = TaskList()
        poll_request.task_list.name = "python-tasklist"

        poll_response, err = service.poll_for_decision_task(poll_request)
        print(json.dumps(poll_response, cls=Encoder, indent=2))
