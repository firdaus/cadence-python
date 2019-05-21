from dataclasses import dataclass, field
from typing import Callable, Dict, Tuple
import inspect
import threading
import logging
import time

from cadence.conversions import camel_to_snake, snake_to_camel
from cadence.workflowservice import WorkflowService

logger = logging.getLogger(__name__)


@dataclass
class WorkerOptions:
    pass


@dataclass
class Worker:
    host: str = None
    port: int = None
    domain: str = None
    task_list: str = None
    options: WorkerOptions = None
    activities: Dict[str, Callable] = field(default_factory=dict)
    workflow_methods: Dict[str, Tuple[type, Callable]] = field(default_factory=dict)
    service: WorkflowService = None
    threads_started: int = 0
    threads_stopped: int = 0
    stop_requested: bool = False

    def register_activities_implementation(self, activities_instance: object, activities_cls_name: str = None):
        cls_name = activities_cls_name if activities_cls_name else type(activities_instance).__name__
        for method_name, fn in inspect.getmembers(activities_instance, predicate=inspect.ismethod):
            if method_name.startswith("_"):
                continue
            self.activities[f'{cls_name}::{camel_to_snake(method_name)}'] = fn
            self.activities[f'{cls_name}::{snake_to_camel(method_name)}'] = fn

    def register_workflow_implementation_type(self, cls: type, workflow_cls_name: str = None):
        cls_name = workflow_cls_name if workflow_cls_name else cls.__name__
        for method_name, fn in inspect.getmembers(cls, predicate=inspect.isfunction):
            if hasattr(fn, "_workflow_method") and fn._workflow_method:
                self.workflow_methods[fn._name] = (cls, fn)
                if "::" in fn._name:
                    _, method_name = fn._name.split("::")
                    self.workflow_methods[f'{cls_name}::{camel_to_snake(method_name)}'] = (cls, fn)
                    self.workflow_methods[f'{cls_name}::{snake_to_camel(method_name)}'] = (cls, fn)

    def start(self):
        from cadence.activity_loop import activity_task_loop
        from cadence.decision_loop import DecisionTaskLoop
        self.threads_stopped = 0
        self.threads_started = 0
        self.stop_requested = False
        if self.activities:
            thread = threading.Thread(target=activity_task_loop, args=(self,))
            thread.start()
            self.threads_started += 1
        if self.workflow_methods:
            decision_task_loop = DecisionTaskLoop(worker=self)
            decision_task_loop.start()
            self.threads_started += 1

    def stop(self):
        self.stop_requested = True
        while self.threads_stopped != self.threads_started:
            time.sleep(5)

    def is_stop_requested(self):
        return self.stop_requested

    def notify_thread_stopped(self):
        self.threads_stopped += 1

