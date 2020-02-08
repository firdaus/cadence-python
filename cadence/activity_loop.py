import datetime
import logging
import json

from cadence.activity import ActivityContext, ActivityTask, complete_exceptionally, complete
from cadence.cadence_types import PollForActivityTaskRequest, TaskListMetadata, TaskList, PollForActivityTaskResponse
from cadence.conversions import json_to_args
from cadence.workflowservice import WorkflowService
from cadence.worker import Worker

logger = logging.getLogger(__name__)


def activity_task_loop(worker: Worker):
    service: WorkflowService = WorkflowService.create(worker.host, worker.port)
    worker.manage_service(service)
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
            task_token = task.task_token
            if not task_token:
                logger.debug("PollForActivityTask has no task_token (expected): %s", task)
                continue

            args = json_to_args(task.input)
            logger.info(f"Request for activity: {task.activity_type.name}")
            fn = worker.activities.get(task.activity_type.name)
            if not fn:
                logger.error("Activity type not found: " + task.activity_type.name)
                continue

            process_start = datetime.datetime.now()
            activity_context = ActivityContext()
            activity_context.service = service
            activity_context.activity_task = ActivityTask.from_poll_for_activity_task_response(task)
            activity_context.domain = worker.domain
            try:
                ActivityContext.set(activity_context)
                return_value = fn(*args)
                if activity_context.do_not_complete:
                    logger.info(f"Not completing activity {task.activity_type.name}({str(args)[1:-1]})")
                    continue
                error = complete(service, task_token, return_value)
                if error:
                    logger.error("Error invoking RespondActivityTaskCompleted: %s", error)
                logger.info(f"Activity {task.activity_type.name}({str(args)[1:-1]}) returned {json.dumps(return_value)}")
            except Exception as ex:
                logger.error(f"Activity {task.activity_type.name} failed: {type(ex).__name__}({ex})", exc_info=1)
                error = complete_exceptionally(service, task_token, ex)
                if error:
                    logger.error("Error invoking RespondActivityTaskFailed: %s", error)
            finally:
                ActivityContext.set(None)
                process_end = datetime.datetime.now()
                logger.info("Process ActivityTask: %dms", (process_end - process_start).total_seconds() * 1000)
    finally:
        worker.notify_thread_stopped()
