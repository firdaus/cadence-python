from dataclasses import dataclass, field
from typing import Callable, Dict
import inspect
import threading
import logging

from cadence.activity_loop import activity_task_loop
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
    service: WorkflowService = None

    def register_activities_implementation(self, activities_instance: object, activities_cls_name: str = None):
        cls_name = activities_cls_name if activities_cls_name else type(activities_instance).__name__
        for method_name, fn in inspect.getmembers(activities_instance, predicate=inspect.ismethod):
            if method_name.startswith("_"):
                continue
            self.activities[f'{cls_name}::{camel_to_snake(method_name)}'] = fn
            self.activities[f'{cls_name}::{snake_to_camel(method_name)}'] = fn

    def start(self):
        thread = threading.Thread(target=activity_task_loop, args=(self,))
        thread.start()
