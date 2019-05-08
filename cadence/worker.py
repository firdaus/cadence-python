from dataclasses import dataclass, field
from typing import Callable, Dict, Tuple
import inspect
import threading
import logging

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

    def register_activities_implementation(self, activities_instance: object, activities_cls_name: str = None):
        cls_name = activities_cls_name if activities_cls_name else type(activities_instance).__name__
        for method_name, fn in inspect.getmembers(activities_instance, predicate=inspect.ismethod):
            if method_name.startswith("_"):
                continue
            self.activities[f'{cls_name}::{camel_to_snake(method_name)}'] = fn
            self.activities[f'{cls_name}::{snake_to_camel(method_name)}'] = fn

    def register_workflow_implementation_type(self, cls: type):
        for method_name, fn in inspect.getmembers(cls, predicate=inspect.isfunction):
            if hasattr(fn, "_workflow_method") and fn._workflow_method:
                self.workflow_methods[fn._name] = (cls, fn)
                if "::" in fn._name:
                    cls_name, method_name = fn._name.split("::")
                    self.workflow_methods[f'{cls_name}::{camel_to_snake(method_name)}'] = (cls, fn)
                    self.workflow_methods[f'{cls_name}::{snake_to_camel(method_name)}'] = (cls, fn)

    def start(self):
        from cadence.activity_loop import activity_task_loop
        from cadence.decision_loop import decision_task_loop
        if self.activities:
            thread = threading.Thread(target=activity_task_loop, args=(self,))
            thread.start()
        if self.workflow_methods:
            thread = threading.Thread(target=decision_task_loop, args=(self,))
            thread.start()
