from unittest import TestCase

from cadence.conversions import camel_to_snake, copy_thrift_to_py, snake_to_camel, copy_py_to_thrift
from cadence.types import PollForActivityTaskResponse, WorkflowExecution, HistoryEvent, EventType
from cadence.thrift import cadence_thrift


class TestCamelToSnake(TestCase):

    def test(self):
        self.assertEqual("schedule_to_close_timeout_seconds",
                         camel_to_snake("scheduleToCloseTimeoutSeconds"))


class TestSnakeToCamel(TestCase):

    def test(self):
        self.assertEqual("scheduleToCloseTimeoutSeconds",
                         snake_to_camel("schedule_to_close_timeout_seconds"))


class TestCopyThriftToPy(TestCase):

    def setUp(self) -> None:
        self.thrift_object = cadence_thrift.shared.PollForActivityTaskResponse()
        self.thrift_object.taskToken = "TASK_TOKEN"
        self.thrift_object.workflowExecution = cadence_thrift.shared.WorkflowExecution()
        self.thrift_object.workflowExecution.workflowId = "WORKFLOW_ID"
        self.thrift_object.workflowExecution.runId = "RUN_ID"

    def test_copy(self):
        obj: PollForActivityTaskResponse = copy_thrift_to_py(self.thrift_object)
        assert isinstance(obj, PollForActivityTaskResponse)
        self.assertEqual("TASK_TOKEN", obj.task_token)
        self.assertEqual("WORKFLOW_ID", obj.workflow_execution.workflow_id)
        self.assertEqual("RUN_ID", obj.workflow_execution.run_id)

    def test_copy_with_enum(self):
        thrift_obj = cadence_thrift.shared.HistoryEvent(eventType=5)
        obj: HistoryEvent = copy_thrift_to_py(thrift_obj)
        self.assertIsInstance(obj, HistoryEvent)
        self.assertEqual(EventType.DecisionTaskStarted, obj.event_type)
        self.assertIsInstance(obj.event_type, EventType)


class TestCopyPyToThrift(TestCase):
    def setUp(self) -> None:
        self.python_object = PollForActivityTaskResponse()
        self.python_object.task_token = "TASK_TOKEN"
        self.python_object.workflow_execution = WorkflowExecution()
        self.python_object.workflow_execution.workflow_id = "WORKFLOW_ID"
        self.python_object.workflow_execution.run_id = "RUN_ID"

    def test_copy(self):
        thrift_object = copy_py_to_thrift(self.python_object)
        self.assertIsInstance(thrift_object, cadence_thrift.shared.PollForActivityTaskResponse)
        self.assertEqual("TASK_TOKEN", thrift_object.taskToken)
        self.assertEqual("WORKFLOW_ID", thrift_object.workflowExecution.workflowId)
        self.assertEqual("RUN_ID", thrift_object.workflowExecution.runId)

    def test_copy_with_enum(self):
        event: HistoryEvent = HistoryEvent()
        event.event_type = EventType.ActivityTaskFailed
        thrift_object = copy_py_to_thrift(event)
        self.assertIsInstance(thrift_object, cadence_thrift.shared.HistoryEvent)
        self.assertEqual(EventType.ActivityTaskFailed, thrift_object.eventType)
        self.assertIsInstance(thrift_object.eventType, int)
        self.assertEqual(int(EventType.ActivityTaskFailed), thrift_object.eventType)

