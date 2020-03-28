# Intro: Fault-Oblivious Stateful Python Code

cadence-python allows you to create Python functions that have their state (local variables etc..) implicitly saved such that if the process/machine fails the state of the function is not lost and can resume from where it left off. 

This programming model is useful whenever you need to ensure that a function runs to completion. For example:

- Business logic involving multiple micro services
- CI/CD pipelines
- Data pipelines
- RPA
- ETL
- Marketing automation / Customer journeys / Customer engagement
- Zapier/IFTTT like end user automation.
- Chat bots
- Multi-step forms
- Scheduler/Cron jobs

Behind the scenes, cadence-python uses [Cadence](https://github.com/uber/cadence) as its backend. 

For more information about the fault-oblivious programming model refer to the Cadence documentation [here](https://cadenceworkflow.io/docs/03_concepts/01_workflows)

## Install Cadencce

```
wget https://raw.githubusercontent.com/uber/cadence/master/docker/docker-compose.yml
docker-compose up
```

## Register `sample` domain

```
docker run --network=host --rm ubercadence/cli:master --do sample domain register -rd 1
```

## Installation cadence-python

```
pip install cadence-client==1.0.0b1
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
    async def get_greeting(self, name: str) -> str:
        raise NotImplementedError


# Workflow Implementation
class GreetingWorkflowImpl(GreetingWorkflow):

    def __init__(self):
        self.greeting_activities: GreetingActivities = Workflow.new_activity_stub(GreetingActivities)

    async def get_greeting(self, name):
        # Place any Python code here that you want to ensure is executed to completion.
        # Note: code in workflow functions must be deterministic so that the same code paths
        # are ran during replay.
        return await self.greeting_activities.compose_greeting("Hello", name)


if __name__ == '__main__':
    factory = WorkerFactory("localhost", 7933, DOMAIN)
    worker = factory.new_worker(TASK_LIST)
    worker.register_activities_implementation(GreetingActivitiesImpl(), "GreetingActivities")
    worker.register_workflow_implementation_type(GreetingWorkflowImpl)
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

## Status / TODO

cadence-python is still under going heavy development. It should be considered EXPERIMENTAL at the moment. A production
version is targeted to be released in ~~September of 2019~~ ~~January 2020~~ ~~March 2020~~ April 2020.

1.0
- [x] Tchannel implementation
- [x] Python-friendly wrapper around Cadence's Thrift API
- [x] Author activities in Python
- [x] Start workflows (synchronously)
- [x] Create workflows
- [x] Workflow execution in coroutines
- [x] Invoke activities from workflows
- [x] ActivityCompletionClient heartbeat, complete, complete_exceptionally
- [x] Activity heartbeat, getHeartbeatDetails and doNotCompleteOnReturn
- [x] Activity retry
- [x] Activity getDomain(), getTaskToken(), getWorkflowExecution()
- [x] Signals
- [x] Queries
- [x] Async workflow execution
- [x] await
- [x] now (currentTimeMillis)
- [x] Sleep
- [x] Loggers
- [x] newRandom
- [x] UUID
- [x] Workflow Versioning
- [x] WorkflowClient.newWorkflowStub(Class workflowInterface, String workflowId);

1.1
- [ ] ActivityStub and Workflow.newUntypedActivityStub
- [ ] Classes as arguments and return values to/from activity and workflow methods
- [ ] WorkflowStub and WorkflowClient.newUntypedWorkflowStub
- [ ] Custom workflow ids through start() and new_workflow_stub()
- [ ] ContinueAsNew
- [ ] Compatibility with Java client
- [ ] Compatibility with Golang client

2.0
- [ ] Sticky workflows

Post 2.0:
- [ ] sideEffect/mutableSideEffect
- [ ] Local activity
- [ ] Parallel activity execution
- [ ] Timers
- [ ] Cancellation Scopes
- [ ] Child Workflows
- [ ] Explicit activity ids for activity invocations


