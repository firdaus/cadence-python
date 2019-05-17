# Generates JSON dumps of workflow history for unit testing purposes
import sys
import dataclasses
import json

from cadence.cadence_types import GetWorkflowExecutionHistoryRequest, WorkflowExecution
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

    history_request = GetWorkflowExecutionHistoryRequest()
    history_request.domain = "sample"
    history_request.execution = WorkflowExecution()
    history_request.execution.workflow_id = sys.argv[1]
    history_request.maximum_page_size = 100

    history_response, err = service.get_workflow_execution_history(history_request)
    if err:
        print(err)
    else:
        print(json.dumps(history_response, cls=Encoder, indent=2))
