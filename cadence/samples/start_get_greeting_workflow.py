from cadence.workflow import workflow_method, WorkflowClient, WorkflowExecutionFailedException, \
    WorkflowExecutionTimedOutException, WorkflowExecutionTerminatedException


class GreetingWorkflow:

    @workflow_method(name='GreetingWorkflow::getGreeting', execution_start_to_close_timeout_seconds=10,
                     task_list='HelloActivity')
    def get_greeting(self, name):
        pass


if __name__ == '__main__':
    client = WorkflowClient.new_client(domain="sample")
    greeting_workflow: GreetingWorkflow = client.new_workflow_stub(GreetingWorkflow)
    try:
        result = greeting_workflow.get_greeting("World")
    except WorkflowExecutionTerminatedException as ex:
        print(f"Workflow terminated: {ex}")
    except WorkflowExecutionTimedOutException as ex:
        print(f"Workflow timed out: {ex}")
    except WorkflowExecutionFailedException as ex:
        print(f"Workflow execution failed: {ex}")
