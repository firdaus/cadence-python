import datetime
import logging
import json

from cadence.cadence_types import PollForActivityTaskRequest, TaskListMetadata, TaskList, PollForActivityTaskResponse, \
    RespondActivityTaskCompletedRequest, RespondActivityTaskFailedRequest
from cadence.conversions import json_to_args
from cadence.workflowservice import WorkflowService

logger = logging.getLogger(__name__)


def activity_task_loop(worker):
    service = WorkflowService.create(worker.host, worker.port)
    logger.info(f"Activity task worker started: {WorkflowService.get_identity()}")
    try:
        while True:
            if worker.is_stop_requested():
                return
            try:
                polling_start = datetime.datetime.now()
                polling_request = PollForActivityTaskRequest()
                polling_request.task_list_metadata = TaskListMetadata()
                polling_request.task_list_metadata.max_tasks_per_second = 200000
                polling_request.domain = worker.domain
                polling_request.identity = WorkflowService.get_identity()
                polling_request.task_list = TaskList()
                polling_request.task_list.name = worker.task_list
                task: PollForActivityTaskResponse
                task, err = service.poll_for_activity_task(polling_request)
                polling_end = datetime.datetime.now()
                logger.debug("PollForActivityTask: %dms", (polling_end - polling_start).total_seconds() * 1000)
            except Exception as ex:
                logger.error("PollForActivityTask error: %s", ex)
                continue
            if err:
                logger.error("PollForActivityTask failed: %s", err)
                continue
            if not task.task_token:
                logger.debug("PollForActivityTask has no task_token (expected): %s", task)
                continue

            args = json_to_args(task.input)
            logger.info(f"Request for activity: {task.activity_type.name}")
            fn = worker.activities.get(task.activity_type.name)
            if not fn:
                logger.error("Activity type not found: " + task.activity_type.name)
                continue

            process_start = datetime.datetime.now()
            try:
                ret = fn(*args)
                respond = RespondActivityTaskCompletedRequest()
                respond.task_token = task.task_token
                respond.result = json.dumps(ret)
                respond.identity = WorkflowService.get_identity()
                _, error = service.respond_activity_task_completed(respond)
                if error:
                    logger.error("Error invoking RespondActivityTaskCompleted: %s", error)
                logger.info(f"Activity {task.activity_type.name}({str(args)[1:-1]}) returned {respond.result}")
            except Exception as ex:
                logger.error(f"Activity {task.activity_type.name} failed: {type(ex).__name__}({ex})", exc_info=1)
                respond: RespondActivityTaskFailedRequest = RespondActivityTaskFailedRequest()
                respond.task_token = task.task_token
                respond.identity = WorkflowService.get_identity()
                respond.details = json.dumps({
                    "detailMessage": f"Python error: {type(ex).__name__}({ex})",
                    "class": "java.lang.Exception"
                })
                respond.reason = "java.lang.Exception"
                _, error = service.respond_activity_task_failed(respond)
                if error:
                    logger.error("Error invoking RespondActivityTaskFailed: %s", error)

            process_end = datetime.datetime.now()
            logger.info("Process ActivityTask: %dms", (process_end - process_start).total_seconds() * 1000)
    finally:
        worker.notify_thread_stopped()
