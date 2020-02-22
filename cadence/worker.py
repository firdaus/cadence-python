from dataclasses import dataclass, field
from typing import Callable, Dict, Tuple, List
import inspect
import threading
import logging
import time

from cadence.conversions import camel_to_snake, snake_to_camel
from cadence.workflow import WorkflowMethod, SignalMethod, QueryMethod
from cadence.workflowservice import WorkflowService

logger = logging.getLogger(__name__)


@dataclass
class WorkerOptions:
    pass


def _find_interface_class(impl_cls) -> type:
    hierarchy = list(inspect.getmro(impl_cls))
    hierarchy.reverse()
    hierarchy.pop(0)  # remove object
    for cls in hierarchy:
        for method_name, fn in inspect.getmembers(cls, predicate=inspect.isfunction):
            # first class with a "_workflow_method" is considered the interface
            if hasattr(fn, "_workflow_method"):
                return cls
    return impl_cls


def _find_metadata_field(cls, metadata_field, method_name):
    for c in inspect.getmro(cls):
        if not hasattr(c, method_name):
            continue
        m = getattr(c, method_name)
        if not hasattr(m, metadata_field):
            continue
        return getattr(m, metadata_field)
    return None


def _get_wm(cls: type, method_name: str) -> WorkflowMethod:
    metadata_field = "_workflow_method"
    return _find_metadata_field(cls, metadata_field, method_name)


def _get_sm(cls: type, method_name: str) -> SignalMethod:
    metadata_field = "_signal_method"
    return _find_metadata_field(cls, metadata_field, method_name)


def _get_qm(cls: type, method_name: str) -> QueryMethod:
    metadata_field = "_query_method"
    return _find_metadata_field(cls, metadata_field, method_name)


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
    service_instances: List[WorkflowService] = field(default_factory=list)

    def register_activities_implementation(self, activities_instance: object, activities_cls_name: str = None):
        cls_name = activities_cls_name if activities_cls_name else type(activities_instance).__name__
        for method_name, fn in inspect.getmembers(activities_instance, predicate=inspect.ismethod):
            if method_name.startswith("_"):
                continue
            self.activities[f'{cls_name}::{camel_to_snake(method_name)}'] = fn
            self.activities[f'{cls_name}::{snake_to_camel(method_name)}'] = fn

    def register_workflow_implementation_type(self, impl_cls: type, workflow_cls_name: str = None):
        cls_name = workflow_cls_name if workflow_cls_name else _find_interface_class(impl_cls).__name__
        if not hasattr(impl_cls, "_signal_methods"):
            impl_cls._signal_methods = {}
        if not hasattr(impl_cls, "_query_methods"):
            impl_cls._query_methods = {}
        for method_name, fn in inspect.getmembers(impl_cls, predicate=inspect.isfunction):
            wm: WorkflowMethod = _get_wm(impl_cls, method_name)
            if wm:
                impl_fn = getattr(impl_cls, method_name)
                self.workflow_methods[wm._name] = (impl_cls, impl_fn)
                if "::" in wm._name:
                    _, method_name = wm._name.split("::")
                    self.workflow_methods[f'{cls_name}::{camel_to_snake(method_name)}'] = (impl_cls, impl_fn)
                    self.workflow_methods[f'{cls_name}::{snake_to_camel(method_name)}'] = (impl_cls, impl_fn)
                continue
            sm: SignalMethod = _get_sm(impl_cls, method_name)
            if sm:
                impl_fn = getattr(impl_cls, method_name)
                impl_cls._signal_methods[sm.name] = impl_fn
                if "::" in sm.name:
                    _, method_name = sm.name.split("::")
                    impl_cls._signal_methods[f'{cls_name}::{camel_to_snake(method_name)}'] = impl_fn
                    impl_cls._signal_methods[f'{cls_name}::{snake_to_camel(method_name)}'] = impl_fn
                continue
            qm: QueryMethod = _get_qm(impl_cls, method_name)
            if qm:
                impl_fn = getattr(impl_cls, method_name)
                impl_cls._query_methods[qm.name] = impl_fn
                if "::" in qm.name:
                    _, method_name = qm.name.split("::")
                    impl_cls._query_methods[f'{cls_name}::{camel_to_snake(method_name)}'] = impl_fn
                    impl_cls._query_methods[f'{cls_name}::{snake_to_camel(method_name)}'] = impl_fn


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

    def stop(self, background=False):
        self.stop_requested = True
        if background:
            for service in self.service_instances:
                service.close()
        else:
            while self.threads_stopped != self.threads_started:
                time.sleep(5)

    def is_stop_requested(self):
        return self.stop_requested

    def notify_thread_stopped(self):
        self.threads_stopped += 1

    def get_workflow_method(self, workflow_type_name: str) -> Tuple[type, Callable]:
        return self.workflow_methods[workflow_type_name]

    def manage_service(self, service: WorkflowService):
        self.service_instances.append(service)


