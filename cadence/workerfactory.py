from dataclasses import dataclass, field
from typing import List

from cadence.worker import Worker, WorkerOptions


@dataclass
class WorkerFactoryOptions:
    pass


@dataclass
class WorkerFactory:
    host: str = None
    port: int = None
    domain: str = None
    options: WorkerFactoryOptions = None
    workers: List[Worker] = field(default_factory=list)

    def new_worker(self, task_list: str, worker_options: WorkerOptions = None) -> Worker:
        worker = Worker(host=self.host, port=self.port, domain=self.domain, task_list=task_list, options=worker_options)
        self.workers.append(worker)
        return worker

    def start(self):
        for worker in self.workers:
            worker.start()
