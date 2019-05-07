import json

from cadence.cadence_types import PollForActivityTaskResponse, RespondActivityTaskCompletedRequest, PollForActivityTaskRequest, \
    TaskList
from cadence.workflowservice import WorkflowService
service = WorkflowService.create("localhost", 7933)
while True:
    task: PollForActivityTaskResponse
    try:
        polling_request = PollForActivityTaskRequest()
        polling_request.domain = "sample"
        polling_request.identity = WorkflowService.get_identity()
        polling_request.task_list = TaskList()
        polling_request.task_list.name = "python-tasklist"
        task, error = service.poll_for_activity_task(polling_request)
    except Exception as ex:
        # Most probably a Timeout
        continue
    if error:
        print("Error: " + error)
        continue
    print("Request: " + str(task))
    input = json.loads(task.input)
    greeting = input[0]
    name = input[1]
    output = json.dumps(greeting + " " + name + "!");

    print(task.task_token)
    respond_activity_completed_request = RespondActivityTaskCompletedRequest()
    respond_activity_completed_request.task_token = task.task_token
    respond_activity_completed_request.result = output
    respond_activity_completed_request.identity = WorkflowService.get_identity()

    _, error = service.respond_activity_task_completed(respond_activity_completed_request)

