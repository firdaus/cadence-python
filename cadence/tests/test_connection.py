from typing import List, Union
from unittest import TestCase

from cadence.connection import TChannelConnection, ThriftFunctionCall
from cadence.frames import CallReqContinueFrame, CallReqFrame

METHOD_NAME = "WorkflowService::StartWorkflowExecution"
SERVICE = "cadence-frontend"


class TestCallReqFrame(TestCase):
    def test_open(self):
        c = TChannelConnection.open("localhost", 7933)
        c.close()


class TestThriftFunctionCall(TestCase):

    def setUp(self) -> None:
        super().setUp()
        self.single_frame = ThriftFunctionCall.create(SERVICE, METHOD_NAME, bytes(100))
        self.multiple_frames = ThriftFunctionCall.create(SERVICE, METHOD_NAME, bytes(100000))

        balance = ThriftFunctionCall.create(SERVICE, METHOD_NAME, bytes()).build_frames(1)[0].space_available()
        self.single_frame_last_argument_frame_boundary = ThriftFunctionCall.create(SERVICE, METHOD_NAME, bytes(balance))

        self.multiple_frames_last_argument_one_byte_over = ThriftFunctionCall.create(SERVICE, METHOD_NAME, bytes(balance + 1))

        first_frame = ThriftFunctionCall.create(SERVICE, " ", bytes(100)).build_frames(1)[0]
        balance = (0xFFFF - first_frame.get_size() + first_frame.args[1].size() + first_frame.args[2].size())
        self.multiple_frames_first_argument_frame_boundary = ThriftFunctionCall.create(SERVICE, " " * balance, bytes(100))

    def test_single_frame_generate(self):
        frames = self.single_frame.build_frames(1)
        self.assertEqual(1, len(frames))
        self.assertEqual(3, len(frames[0].args))

    def test_single_frame_read(self):
        self.validate_equal(self.single_frame)

    def validate_equal(self, original_call: ThriftFunctionCall):
        call = ThriftFunctionCall()
        for f in original_call.build_frames(1):
            call.process_frame(f)
        self.assertEqual(1, call.message_id)
        self.assertEqual(SERVICE, call.service)
        self.assertEqual(original_call.method_name, call.method_name)
        self.assertEqual(original_call.thrift_payload, call.thrift_payload)
        self.assertEqual(original_call.tchannel_headers, call.tchannel_headers)
        self.assertEqual(original_call.application_headers, call.application_headers)
        self.assertEqual(original_call.ttl, call.ttl)

    def test_multiple_frames(self):
        frames = self.multiple_frames.build_frames(1)
        self.assertEqual(2, len(frames))
        self.assertEqual(True, frames[0].is_more_fragments_follow())
        self.assertEqual(3, len(frames[0].args))

        self.assertEqual(False, frames[1].is_more_fragments_follow())
        self.assertEqual(1, len(frames[1].args))

    def test_multiple_frames_read(self):
        self.validate_equal(self.multiple_frames)

    def test_single_frame_last_argument_frame_boundary(self):
        frames = self.single_frame_last_argument_frame_boundary.build_frames(1)
        self.assertEqual(1, len(frames))

    def test_single_frame_last_argument_frame_boundary_read(self):
        self.validate_equal(self.single_frame_last_argument_frame_boundary)

    def test_multiple_frames_last_argument_one_byte_over(self):
        frames = self.multiple_frames_last_argument_one_byte_over.build_frames(1)
        self.assertEqual(2, len(frames))
        self.assertEqual(3, len(frames[0].args))
        self.assertEqual(1, len(frames[1].args))
        self.assertEqual(1, len(frames[1].args[0].buf))

    def test_multiple_frames_last_argument_one_byte_over_read(self):
        self.validate_equal(self.multiple_frames_last_argument_one_byte_over)

    def test_frame_boundary_first_argument(self):
        frames: List[Union[CallReqFrame, CallReqContinueFrame]] = self.multiple_frames_first_argument_frame_boundary.build_frames(1)
        self.assertEqual(2, len(frames))
        self.assertEqual(1, len(frames[0].args))
        self.assertEqual(3, len(frames[1].args))
        self.assertEqual(0, len(frames[1].args[0].buf))

    def test_frame_boundary_first_argument_read(self):
        self.validate_equal(self.multiple_frames_first_argument_frame_boundary)
