from unittest import TestCase

from cadence.errors import find_error, InternalServiceError, WorkflowExecutionAlreadyStartedError
from cadence.thrift import cadence


class TestError(TestCase):

    def setUp(self) -> None:
        self.internalServiceError = cadence.shared.InternalServiceError("ERROR")
        self.sessionAlreadyExistError = cadence.shared.WorkflowExecutionAlreadyStartedError("ERROR", "REQUEST-ID",
                                                                                            "RUN-ID")

    def test_internal_server_error(self):
        response = cadence.WorkflowService.StartWorkflowExecution.response(
            internalServiceError=self.internalServiceError)
        error = find_error(response)
        self.assertIsInstance(error, InternalServiceError)
        self.assertEqual("ERROR", error.message)

    def test_session_already_exists_error(self):
        response = cadence.WorkflowService.StartWorkflowExecution.response(
            sessionAlreadyExistError=self.sessionAlreadyExistError)
        error = find_error(response)
        self.assertIsInstance(error, WorkflowExecutionAlreadyStartedError)
        self.assertEqual("ERROR", error.message)
        self.assertEqual("REQUEST-ID", error.start_request_id)
        self.assertEqual("RUN-ID", error.run_id)
