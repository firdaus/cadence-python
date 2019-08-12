import datetime
import logging
from typing import NoReturn, Type, Sequence, Dict
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

            polling_start = datetime.datetime.now()
            try:
                task = service.poll_for_activity_task(polling_request)
            except Exception as ex:
                logger.error("PollForActivityTask error: %s", ex)
                continue
            polling_end = datetime.datetime.now()
            polling_total = polling_end - polling_start
            logger.info(
                f"PollForActivityTask: done. Start: {polling_start.total_seconds()}, End: {polling_end.total_seconds()}, Total: {polling_total.total_seconds()}"
            )

            # Process activity task
            try:
                ret = worker.run_task(task)
                response = RespondActivityTaskCompletedRequest(
                    task_token=task.task_token,
                    result=ret,
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
                        {"python_error": f"{type(ex).__name__}({ex})"}
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
