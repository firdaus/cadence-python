import datetime
import logging
import json
from typing import NoReturn, Type, Sequence, Dict

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

            polling_start = datetime.datetime.now()
            try:
                task = service.poll_for_activity_task(polling_request)
            except RuntimeError as ex:
                logger.error("PollForActivityTask RuntimeError: %s", ex)
                continue
            except Exception as ex:
                logger.error("PollForActivityTask error: %s", ex)
                continue
            polling_end = datetime.datetime.now()
            polling_total = polling_end - polling_start
            logger.debug(
                f"PollForActivityTask: done. Start: {polling_start.total_seconds()}, End: {polling_end.total_seconds()}, Total: {polling_total.total_seconds()}"
            )

            # Process activity task
            try:
                ret = handle_task(task,worker.activities)
                response = RespondActivityTaskCompletedRequest(
                    task_token=task.task_token,
                    result=json.dumps(ret),
                    identity=WorkflowService.get_identity(),
                )
                service.respond_activity_task_completed(response)
            except Exception as ex:
                logger.error(
                    f"Activity {task.activity_type.name} failed: {type(ex).__name__}({ex})",
                    exc_info=1)
                response: RespondActivityTaskFailedRequest
                response = RespondActivityTaskFailedRequest(
                    task_token=task.task_token,
                    reason="SOMTHING WENT WRONG",
                    identity=WorkflowService.get_identity(),
                    details=json.dumps({
                        "detailMessage":
                        f"Python error: {type(ex).__name__}({ex})"
                    }))
                try:
                    service.respond_activity_task_failed(response)
                except Exception as ex:
                    logger.error("Error invoking RespondActivityTaskFailed: %s", ex)
                    continue

            logger.info("Process ActivityTask: done")
    except Exception as ex:
        logger.fatal(f"activity_task_loop: Uncought exception in main loop.",exec_info=True)
    finally:
        worker.notify_thread_stopped()





def handle_task(task, activities) -> Dict:
    def handle_error(msg: str, exception: Type[Exception]) -> NoReturn:
        logger.error(msg)
        raise exception(msg)

    # TODO: finish this one
    if not task.task_token:
        handle_error("task.task_token was not provided, but is expected.",
                     RuntimeError)
    if task.activity_type.name not in activities:
        handle_error(
            f"handle_task: Activity type {task.activity_type.name} not found",
            RuntimeError)
    fn = activities[task.activity_type.name]
    try:
        args = json.loads(task.input)
    except json.JSONDecodeError as ex:
        handle_error(f"handle_task: Json decoding failed: {ex}", RuntimeError)

    if not isinstance(args,Sequence):
        handle_error(f"handle_task: Args should be a Sequence but where {type(args)}. args=\n{args}",RuntimeError)
    
    logger.debug(f"handle_task: Calling activity fn with args:\n%s",args)
    try:
        ret_val= fn(*args)
    except Exception as ex:
        handle_error(f"handle_task: Exception when running activity. Exception:\n{ex}",RuntimeError)
    logger.debug(f"handle_task: Activity fn successfully returned. Result:\n%s",ret_val)
    return ret_val
