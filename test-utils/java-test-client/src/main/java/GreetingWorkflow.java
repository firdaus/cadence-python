import com.uber.cadence.client.WorkflowClient;
import com.uber.cadence.client.WorkflowOptions;
import com.uber.cadence.workflow.WorkflowMethod;

public interface GreetingWorkflow {
    @WorkflowMethod(executionStartToCloseTimeoutSeconds = 60 * 5)
    String getGreeting(String name);

    static GreetingWorkflow getStub(String taskList) {
        WorkflowClient workflowClient = WorkflowClient.newInstance("test-domain");

        return workflowClient.newWorkflowStub(GreetingWorkflow.class,
                new WorkflowOptions.Builder().setTaskList(taskList).build());
    }
}
