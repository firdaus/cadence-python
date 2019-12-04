import json
from unittest.mock import MagicMock, Mock

import pytest

from cadence.activity import ActivityContext
from cadence.cadence_types import RecordActivityTaskHeartbeatRequest
from cadence.errors import BadRequestError
from cadence.exceptions import ActivityCancelledException
from cadence.workflowservice import WorkflowService


@pytest.fixture
def activity_context():
    activity_context = ActivityContext()
    activity_context.service = MagicMock()
    activity_context.task_token = "task-token"
    return activity_context


def test_heartbeat(activity_context):
    response = Mock()
    response.cancel_requested = False
    activity_context.service.record_activity_task_heartbeat = Mock(return_value=(response, None))
    activity_context.heartbeat("payload")
    args, kwargs = activity_context.service.record_activity_task_heartbeat.call_args_list[0]
    assert isinstance(args[0], RecordActivityTaskHeartbeatRequest)
    request: RecordActivityTaskHeartbeatRequest = args[0]
    assert request.details == json.dumps("payload")
    assert request.task_token == "task-token"
    assert request.identity == WorkflowService.get_identity()


def test_heartbeat_error(activity_context):
    response = Mock()
    response.cancel_requested = False
    with pytest.raises(BadRequestError):
        activity_context.service.record_activity_task_heartbeat = Mock(return_value=(response,
                                                                                     BadRequestError("error message")))
        activity_context.heartbeat("payload")


def test_heartbeat_cancel_requested(activity_context):
    response = Mock()
    response.cancel_requested = True
    with pytest.raises(ActivityCancelledException):
        activity_context.service.record_activity_task_heartbeat = Mock(return_value=(response, None))
        activity_context.heartbeat("payload")
