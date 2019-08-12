import datetime
import logging
import json

from cadence.cadence_types import PollForActivityTaskRequest, TaskListMetadata, TaskList, PollForActivityTaskResponse, \
    RespondActivityTaskCompletedRequest, RespondActivityTaskFailedRequest
from cadence.workflowservice import WorkflowService

logger = logging.getLogger(__name__)


def activity_task_loop(worker):
    service = WorkflowService.create(worker.host, worker.port)
    logger.info(
        f"Activity task worker started: {WorkflowService.get_identity()}")

    polling_request = PollForActivityTaskRequest(
        domain=worker.domain,
        task_list=TaskList(name=worker.task_list),
        identity=WorkflowService.get_identity(),
        task_list_metadata=TaskListMetadata(max_tasks_per_second=200000))

    task: PollForActivityTaskResponse

    try:
        while True:
            if worker.is_stop_requested():
                return

            # fetch activity task 
            # TODO: Add back polling time
            try:
                task, err = service.poll_for_activity_task(polling_request)
                if err:
                    logger.error("PollForActivityTask failed: %s", err)
                    continue
                # TODO: move this one to handle_task() or check 
                elif not task.task_token:
                    logger.debug("PollForActivityTask has no task_token (expected): %s", task)
                    continue
                logger.debug("PollForActivityTask: done")
            except Exception as ex:
                logger.error("PollForActivityTask error: %s", ex)
                continue
            
            # Process activity task
            # TODO: Add processing polling time
            try:  
                ret = handle_task(task, worker.activities)
                respond = RespondActivityTaskCompletedRequest(
                    task_token=task.task_token,
                    result = json.dumps(ret),
                    identity = WorkflowService.get_identity(),
                )
                _, err = service.respond_activity_task_completed(respond)
                if err:
                    logger.error("Error invoking RespondActivityTaskCompleted: %s", error)
            except Exception as ex:
                logger.error(f"Activity {task.activity_type.name} failed: {type(ex).__name__}({ex})",exc_info=1)
                respond: RespondActivityTaskFailedRequest 
                respond = RespondActivityTaskFailedRequest(
                    task_token=task.task_token,
                    reason="SOMTHING WENT WRONG",
                    identity=WorkflowService.get_identity(),
                    details=json.dumps({
                        "detailMessage": f"Python error: {type(ex).__name__}({ex})"
                    })
                )
                _, error = service.respond_activity_task_failed(respond)
                if error:
                    logger.error("Error invoking RespondActivityTaskFailed: %s", error)
                    
            logger.info("Process ActivityTask: done")
            
    finally:
        worker.notify_thread_stopped()


def handle_task(task, activities):
    # TODO: finish this one
    args = json.loads(task.input)
    if not args:
        # TODO: through acception
    # fn = worker.activities.get(task.activity_type.name)
    # if not fn:
    #     logger.error("Activity type not found: " + task.activity_type.name)
        
    # return fn(*args)
    return


def handle_task_err(task):
    return
    
    