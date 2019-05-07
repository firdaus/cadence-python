import inspect

from cadence.cadence_types import WorkflowIdReusePolicy


def get_workflow_method_name(method):
    return method.__qualname__.replace(".", "::")


def workflow_method(func=None,
                    name=None,
                    workflow_id=None,
                    workflow_id_reuse_policy=WorkflowIdReusePolicy.AllowDuplicateFailedOnly,
                    execution_start_to_close_timeout_seconds=None,
                    task_start_to_close_timeout_seconds=None,
                    task_list=None):
    def wrapper(fn):
        fn._name = name if name else get_workflow_method_name(fn)
        fn._workflow_id = workflow_id
        fn._workflow_id_reuse_policy = workflow_id_reuse_policy
        fn._execution_start_to_close_timeout_seconds = execution_start_to_close_timeout_seconds
        fn._task_start_to_close_timeout_seconds = task_start_to_close_timeout_seconds
        fn._task_list = task_list
        return fn

    if func and inspect.isfunction(func):
        return wrapper(func)
    else:
        return wrapper

