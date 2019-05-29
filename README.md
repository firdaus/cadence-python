# Python framework for Cadence Workflow Service

[Cadence](https://github.com/uber/cadence) is a workflow engine developed at Uber Engineering. With this framework, workflows and activities managed by Cadence can be implemented in Python code.

## Status / TODO

cadence-python is still under going heavy development. It should be considered EXPERIMENTAL at the moment. A production
version is targeted to be released in September of 2019.

- [x] Tchannel implementation
- [x] Python-friendly wrapper around Cadence's Thrift API
- [x] Author activities in Python
- [x] Start workflows (synchronously)
- [x] Create workflows
- [x] Workflow execution in coroutines
- [x] Invoke activities from workflows
- [ ] Activity heartbeating and doNotCompleteOnReturn
- [ ] Activity retry
- [ ] Sticky workflows
- [ ] Signals
- [ ] Queries
- [ ] Async workflow execution
- [ ] await
- [ ] currentTimeMillis
- [ ] Timers
- [ ] Sleep
- [ ] Loggers
- [ ] newRandom
- [ ] UUID
- [ ] Workflow Versioning

Post 1.0:
- [ ] sideEffect/mutableSideEffect
- [ ] Parallel activity execution
- [ ] Cancellation Scopes
- [ ] Child Workflows

## Installation

```
pip install cadence-client
```

## Hello World Sample

```
import sys
import logging
from cadence.activity_method import activity_method
from cadence.workerfactory import WorkerFactory
from cadence.workflow import workflow_method, Workflow, WorkflowClient

logging.basicConfig(level=logging.DEBUG)

TASK_LIST = "HelloActivity-python-tasklist"
DOMAIN = "sample"


# Activities Interface
class GreetingActivities:
    @activity_method(task_list=TASK_LIST, schedule_to_close_timeout_seconds=2)
    def compose_greeting(self, greeting: str, name: str) -> str:
        raise NotImplementedError


# Activities Implementation
class GreetingActivitiesImpl:
    def compose_greeting(self, greeting: str, name: str):
        return greeting + " " + name + "!"


# Workflow Interface
class GreetingWorkflow:
    @workflow_method(execution_start_to_close_timeout_seconds=10, task_list=TASK_LIST)
    def get_greeting(self, name: str) -> str:
        raise NotImplementedError


# Workflow Implementation
class GreetingWorkflowImpl:

    def __init__(self):
        self.greeting_activities: GreetingActivities = Workflow.new_activity_stub(GreetingActivities)

    @workflow_method(impl=True)
    async def get_greeting(self, name):
        return await self.greeting_activities.compose_greeting("Hello", name)


if __name__ == '__main__':
    factory = WorkerFactory("localhost", 7933, DOMAIN)
    worker = factory.new_worker(TASK_LIST)
    worker.register_activities_implementation(GreetingActivitiesImpl(), "GreetingActivities")
    worker.register_workflow_implementation_type(GreetingWorkflowImpl, "GreetingWorkflow")
    factory.start()

    client = WorkflowClient.new_client(domain=DOMAIN)
    greeting_workflow: GreetingWorkflow = client.new_workflow_stub(GreetingWorkflow)
    result = greeting_workflow.get_greeting("Python")
    print(result)

    print("Stopping workers....")
    worker.stop()
    print("Workers stopped...")
    sys.exit(0)
```
