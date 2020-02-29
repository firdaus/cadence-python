import inspect
from typing import Callable


def get_replay_aware_interceptor(fn: Callable):
    def interceptor(*args, **kwargs):
        from cadence.decision_loop import ITask
        task: ITask = ITask.current()
        if not task.decider.decision_context.is_replaying():
            return fn(*args, **kwargs)

    return interceptor


def make_replay_aware(target: object):
    # TODO: Consider using metaclasses instead
    if hasattr(target, "_cadence_python_intercepted"):
        return target
    for name, fn in inspect.getmembers(target):
        if inspect.ismethod(fn):
            setattr(target, name, get_replay_aware_interceptor(fn))
    target._cadence_python_intercepted = True
    return target
