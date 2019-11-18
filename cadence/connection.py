from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from io import BytesIO
from typing import IO, List, Union, Optional, Dict

from cadence.frames import InitReqFrame, Frame, Arg, CallReqFrame, CallReqContinueFrame, CallResFrame, \
    CallResContinueFrame, FrameWithArgs, CallFlags, ErrorFrame
from cadence.ioutils import IOWrapper
from cadence.kvheaders import KVHeaders
from cadence.tchannel import TChannelException


class FragmentGenerator:
    def __init__(self):
        pass

    def get_args(self) -> List[bytes]:
        raise NotImplementedError()

    def get_initial_frame(self) -> FrameWithArgs:
        raise NotImplementedError()

    def get_continue_frame(self) -> FrameWithArgs:
        raise NotImplementedError()

    def build_frames(self, message_id) -> List[FrameWithArgs]:
        args: List[bytes] = self.get_args()
        frames = []
        while args:
            frame: FrameWithArgs = self.get_initial_frame() if not frames else self.get_continue_frame()
            frame.id = message_id

            while args and not frame.is_full():
                buf: bytes = args[0]
                n = len(buf)
                avail = frame.space_available() - 2  # two byte required for argument length
                if avail <= 0:
                    break

                to_write = n if avail >= n else avail
                arg = Arg(buf[0:to_write])
                frame.args.append(arg)

                buf = buf[to_write:]
                n = len(buf)

                # 1st and 2nd args that end at a frame boundary need an empty arg at the
                # start of the next frame
                if not n and not (len(args) > 1 and frame.is_frame_boundary()):
                    args.pop(0)
                else:
                    args[0] = buf

            if args:
                assert isinstance(frame, CallFlags) and isinstance(frame, FrameWithArgs)
                frame.set_more_fragments_follow(True)

            frames.append(frame)

        return frames


@dataclass
class ArgValue:
    value: bytes = bytes()
    complete: bool = False


class FragmentReader:
    def __init__(self):
        self.args = [ArgValue(), ArgValue(), ArgValue()]

    def get_incomplete_arg(self):
        for a in self.args:
            if not a.complete:
                return a
        return None

    def process_frame(self, frame: Union[FrameWithArgs]):
        self.on_load_frame(frame)
        frame_args_offset = 0
        current_arg = self.get_incomplete_arg()
        while current_arg and frame_args_offset < len(frame.args):
            frame_arg = frame.args[frame_args_offset]
            current_arg.value += frame_arg.buf
            assert isinstance(frame, (CallFlags, FrameWithArgs))
            if not frame.is_more_fragments_follow() or frame_args_offset + 1 < len(frame.args):
                current_arg.complete = True
            current_arg = self.get_incomplete_arg()
            frame_args_offset += 1

        if self.is_complete():
            self.on_args_complete(
                self.args[0].value,
                self.args[1].value,
                self.args[2].value,
            )

    def is_complete(self):
        for a in self.args:
            if not a.complete:
                return False
        return True

    def on_load_frame(self, frame: Union[FrameWithArgs]):
        raise NotImplementedError()

    def on_args_complete(self, arg1: bytes, arg2: bytes, arg3: bytes):
        raise NotImplementedError()


# noinspection PyAbstractClass
class ThriftArgScheme(FragmentGenerator, FragmentReader):
    def __init__(self):
        FragmentGenerator.__init__(self)
        FragmentReader.__init__(self)
        self.method_name = None              # arg1
        self.thrift_payload = None           # arg3
        self.application_headers = None      # arg2

    def on_args_complete(self, arg1: bytes, arg2: bytes, arg3: bytes):
        self.process_arg1(arg1)
        self.process_arg2(arg2)
        self.process_arg3(arg3)

    def process_arg1(self, b):
        self.method_name = str(b, "utf-8")

    def process_arg2(self, b):
        f: BytesIO = BytesIO(b)
        wrapper: IOWrapper = IOWrapper(f)
        h: KVHeaders = KVHeaders.read_kv_headers(wrapper, 2, "ThriftFunctionResponse")
        self.application_headers = h.d

    def process_arg3(self, b):
        self.thrift_payload = b

    def build_arg1(self) -> bytes:
        f = BytesIO()
        wrapper: IOWrapper = IOWrapper(f)
        wrapper.write_string(self.method_name)
        wrapper.flush()
        return f.getvalue()

    def build_arg2(self) -> bytes:
        f = BytesIO()
        wrapper: IOWrapper = IOWrapper(f)
        h = KVHeaders(self.application_headers, 2)
        h.write_headers(wrapper)
        return f.getvalue()

    def build_arg3(self) -> bytes:
        return self.thrift_payload

    def get_args(self) -> List[bytes]:
        args: List[bytes] = [self.build_arg1(), self.build_arg2(), self.build_arg3()]
        return args


class ThriftFunctionCall(ThriftArgScheme):

    service: Optional[str]
    method_name: str
    thrift_payload: bytes
    tchannel_headers: Optional[dict]
    application_headers: Dict[str, str]
    ttl: int

    @classmethod
    def create(cls, service: str, method_name: str, thrift_payload: bytes):
        o = cls()
        o.service = service
        o.method_name = method_name
        o.thrift_payload = thrift_payload
        o.tchannel_headers = cls.default_tchannel_headers()
        o.application_headers = cls.default_application_headers()
        # PollForActivityTask is hardcoded on the server to timeout at
        # 60 seconds, so the ttl needs to be slightly more so that it
        # does not fail.
        o.ttl = 61000
        return o

    @staticmethod
    def default_tchannel_headers():
        return {
            "as": "thrift",
            "re": "c",
            "cn": "cadence-client"
        }

    @staticmethod
    def default_application_headers():
        return {
            "user-name": os.environ.get("LOGNAME", os.getlogin()),
            "host-name": socket.gethostname(),
            # Copied from Java client
            "cadence-client-library-version": "2.2.0",
            "cadence-client-feature-version": "1.0.0"
        }

    def __init__(self):
        super().__init__()
        self.service = None
        self.tchannel_headers = None
        self.ttl = 0
        self.message_id = 0

    # Functions for frame reading

    def on_load_frame(self, frame: FrameWithArgs):
        if not frame.TYPE == CallReqFrame.TYPE:
            return
        # noinspection PyTypeChecker
        frame: CallReqFrame = frame
        self.message_id = frame.id
        self.service = frame.service
        self.ttl = frame.ttl
        self.tchannel_headers = frame.headers.d

    # Functions for frame generation

    def get_initial_frame(self) -> FrameWithArgs:
        frame: CallReqFrame = CallReqFrame()
        frame.ttl = self.ttl
        frame.service = self.service
        frame.headers.d.update(self.tchannel_headers)
        return frame

    def get_continue_frame(self) -> FrameWithArgs:
        frame: CallReqContinueFrame = CallReqContinueFrame()
        return frame


class ThriftFunctionResponse(ThriftArgScheme):

    thrift_payload: bytes
    method_name: str
    code: Optional[int]

    @classmethod
    def create(cls, code: int, thrift_payload):
        o = cls()
        o.code = code
        o.method_name = ""
        o.thrift_payload = thrift_payload
        o.tchannel_headers = cls.default_tchannel_headers()
        o.application_headers = cls.default_application_headers()
        return o

    @staticmethod
    def default_tchannel_headers():
        return {
            "as": "thrift"
        }

    @staticmethod
    def default_application_headers():
        return {
            "$rpc$-service": "dummy"
        }

    def __init__(self):
        ThriftArgScheme.__init__(self)
        self.message_id = None
        self.code = None
        self.tchannel_headers = None

    # Functions for frame reading

    def on_load_frame(self, frame: Union[FrameWithArgs]):
        if not frame.TYPE == CallResFrame.TYPE:
            return
        # noinspection PyTypeChecker
        frame: CallResFrame = frame
        self.message_id = frame.id
        self.code = frame.code
        self.tchannel_headers = frame.headers.d

    # Functions for frame generation

    def get_initial_frame(self) -> FrameWithArgs:
        frame: CallResFrame = CallResFrame()
        frame.code = self.code
        frame.headers.d.update(self.tchannel_headers)
        return frame

    def get_continue_frame(self) -> FrameWithArgs:
        frame: CallResContinueFrame = CallResContinueFrame()
        return frame


class TChannelConnection:

    file: IO
    wrapper: IOWrapper
    s: socket.socket

    @classmethod
    def open(cls, host: object, port: object) -> TChannelConnection:
        s: socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        return cls(s)

    def __init__(self, s: socket):
        self.s = s
        self.file = self.s.makefile("rwb")
        self.wrapper = IOWrapper(self.file)
        self.current_id = -1

        self.handshake()

    def new_id(self):
        self.current_id += 1
        return self.current_id

    def handshake(self):
        req: InitReqFrame = InitReqFrame()
        req.id = self.new_id()
        req.headers.d["host_port"] = "0.0.0.0:0"
        req.headers.d["process_name"] = "python-process"
        self.write_frame(req)

        res = self.read_frame()
        if res.TYPE != 0x02:
            raise Exception("Unexpected response from server")

    def write_frame(self, frame: Frame):
        frame.write(self.wrapper)
        self.wrapper.flush()

    def read_frame(self):
        frame = Frame.read_frame(self.wrapper)
        if isinstance(frame, ErrorFrame):
            raise TChannelException(error_frame=frame)
        return frame

    def close(self):
        self.s.close()

    def call_function(self, call: ThriftFunctionCall) -> ThriftFunctionResponse:
        frames = call.build_frames(self.new_id())
        for frame in frames:
            self.write_frame(frame)
        response = ThriftFunctionResponse()
        while not response.is_complete():
            frame = self.read_frame()
            if frame.TYPE not in (CallResFrame.TYPE, CallResContinueFrame.TYPE):
                raise Exception("Unexpected type: " + Frame.TYPE)
            assert isinstance(frame, FrameWithArgs)
            response.process_frame(frame)
        return response
