from __future__ import annotations

from typing import Type, Dict, Optional, IO, List

from .ioutils import IOWrapper
from .kvheaders import KVHeaders

FRAME_HEADER_SIZE = 16


# Helper class to make get_payload_size() functions more readable
class LenHelper(object):
    def __getattr__(self, name):
        def fn(*args):
            return args[0]
        return fn


_ = LenHelper()


class FrameHeader:
    """
    size:2 type:1 reserved:1 id:4
    reserved:8
    """
    @classmethod
    def read_header(cls, fp: IOWrapper) -> FrameHeader:
        size = fp.read_short("header.size")
        payload_type = fp.read_byte("header.payload_type")
        reserved1 = fp.read_byte("header.reserved1")
        frame_id = fp.read_long("header.id")
        reserved2 = fp.read_bytes(8, "header.reserved2")
        return cls(size, payload_type, frame_id)

    def __init__(self, size: int = None, payload_type: int = None, frame_id: int = None):
        self.size = size
        self.payload_type = payload_type
        self.id = frame_id


class Frame:
    TYPE = None

    @staticmethod
    def read_frame(wrapper: IOWrapper) -> Frame:
        header: FrameHeader = FrameHeader.read_header(wrapper)
        frame_types: Dict[int, Type[Frame]] = {
            0x01: InitReqFrame,
            0x02: InitResFrame,
            0x03: CallReqFrame,
            0x04: CallResFrame,
            0x13: CallReqContinueFrame,
            0x14: CallResContinueFrame,
            0Xff: ErrorFrame
        }

        frame_cls: Optional[Type[Frame]] = frame_types.get(header.payload_type)
        if not frame_cls:
            raise NotImplementedError("Payload type: %s " % hex(header.payload_type))
        frame: Frame = frame_cls()
        frame.read(header, wrapper)
        return frame

    def __init__(self):
        self.id = None

    def read(self, header: FrameHeader, fp: IOWrapper):
        self.id = header.id
        self.read_payload(fp, header.size - FRAME_HEADER_SIZE)

    def read_payload(self, fp: IOWrapper, size: int):
        raise NotImplementedError()

    def write(self, wrapper: IOWrapper):
        self.write_header(wrapper)
        self.write_payload(wrapper)

    def write_header(self, fp: IOWrapper):
        fp.write_short(self.get_size())
        fp.write_byte(self.TYPE)
        fp.write_byte(0)
        fp.write_long(self.id)
        fp.write_bytes(bytes(8))

    def get_size(self):
        return FRAME_HEADER_SIZE + self.get_payload_size()

    def get_payload_size(self):
        raise NotImplementedError()

    def write_payload(self, fp: IOWrapper):
        raise NotImplementedError()

    def is_full(self):
        size = self.get_size()
        assert size <= 0xFFFF
        return size == 0xFFFF

    def space_available(self):
        size = self.get_size()
        return 0xFFFF - size

    def has_space_available(self, n):
        return n >= (0xFFFF - self.get_size())

    def is_frame_boundary(self):
        # Frame cannot fit any more arguments
        return self.has_space_available(3)


class InitReqFrame(Frame):
    VERSION = 2
    TYPE = 0x01

    def __init__(self):
        super().__init__()
        self.headers = KVHeaders(len_size=2)
        self.version = self.VERSION

    def read_payload(self, fp: IOWrapper, size: int):
        self.version = fp.read_short("initreq.version")
        self.headers = KVHeaders.read_kv_headers(fp, 2, "initreq.headers")

    def get_payload_size(self):
        return 2 + self.headers.size()

    def write_payload(self, fp: IOWrapper):
        fp.write_short(self.VERSION)
        self.headers.write_headers(fp)


class InitResFrame(Frame):
    VERSION = 2
    TYPE = 0x02

    def __init__(self):
        super().__init__()
        self.headers = KVHeaders(len_size=2)
        self.version = self.VERSION

    def read_payload(self, fp: IOWrapper, size: int):
        self.version = fp.read_short("initres.version")
        self.headers = KVHeaders.read_kv_headers(fp, 2, "initres.headers")

    def get_payload_size(self):
        return 2 + self.headers.size()

    def write_payload(self, fp: IOWrapper):
        fp.write_short(self.VERSION)
        self.headers.write_headers(fp)


class Arg:

    @classmethod
    def read_arg(cls, fp: IOWrapper, offset, payload_size, possible_fragment, field):
        arg_length = fp.read_short(field + ".arg_length")
        offset += 2
        buf = fp.read_bytes(arg_length, field + ".arg")
        offset += arg_length
        is_fragment = False
        # if there is more data
        if possible_fragment and offset < payload_size:
            is_fragment = False
        elif possible_fragment and offset == payload_size:
            is_fragment = True
        elif possible_fragment:
            raise Exception("Malformed frame argument")
        return cls(buf, is_fragment)

    def __init__(self, buf, is_fragment=False):
        self.buf = buf
        self.is_fragment = is_fragment

    def size(self):
        return 2 + len(self.buf)

    def write_arg(self, fp: IOWrapper):
        fp.write_short(len(self.buf))
        fp.write_bytes(self.buf)


class CallFlags:
    FLAG_MORE_FRAGMENTS_FOLLOW = 0x01
    # noinspection PyPep8
    FLAG_REQUEST_STREAMING     = 0x02

    def __init__(self):
        self.flags = 0

    def set_more_fragments_follow(self, b):
        if b:
            self.flags = self.flags | self.FLAG_MORE_FRAGMENTS_FOLLOW
        else:
            self.flags = self.flags & ~self.FLAG_MORE_FRAGMENTS_FOLLOW

    def is_more_fragments_follow(self):
        return self.flags & self.FLAG_MORE_FRAGMENTS_FOLLOW

    def set_request_streaming(self, b):
        if b:
            self.flags = self.flags | self.FLAG_REQUEST_STREAMING
        else:
            self.flags = self.flags & ~self.FLAG_REQUEST_STREAMING

    def is_request_streaming(self):
        return self.flags & self.FLAG_REQUEST_STREAMING


class FrameWithArgs(Frame):
    args: List[Arg]

    def __init__(self):
        self.args = []


class CallReqFrame(FrameWithArgs, CallFlags):
    """
    flags:1 ttl:4 tracing:25
    service~1 nh:1 (hk~1 hv~1){nh}
    csumtype:1 (csum:4){0,1} arg1~2 arg2~2 arg3~2
    """
    TYPE = 0x03

    def __init__(self):
        FrameWithArgs.__init__(self)
        CallFlags.__init__(self)
        self.ttl = 0
        self.tracing = bytes(25)
        self.service = ""
        self.headers = KVHeaders({}, 1)
        self.csumtype = 0

    # noinspection PyPep8
    def read_payload(self, fp: IOWrapper, size: int):
        offset = 0
        self.flags = fp.read_byte("callreq.flags"); offset += 1;
        self.ttl = fp.read_long("callreq.ttl"); offset += 4;
        self.tracing = fp.read_bytes(25, "callreq.tracing"); offset += 25;
        service_len = fp.read_byte('callreq.service_len'); offset += 1;
        self.service = fp.read_string(service_len, "callreq.service"); offset += service_len;
        self.headers = KVHeaders.read_kv_headers(fp, 1, "callreq.headers"); offset += self.headers.size();
        self.csumtype = fp.read_byte("callreq.csumtype"); offset += 1;
        if self.csumtype != 0:
            raise NotImplementedError("Checksum type not supported")
        self.args = []
        arg_count = 1
        while offset < size:
            arg = Arg.read_arg(fp, offset, size, self.is_more_fragments_follow(), "callreq.args[%d]" % arg_count)
            self.args.append(arg); offset += arg.size();
            arg_count += 1

    def get_payload_size(self):
        return (_.flags(1) + _.ttl(4) + _.tracing(25) +
                _.service_len(1) + len(self.service) + self.headers.size() +
                _.csumtype(1) + sum([arg.size() for arg in self.args]))

    # noinspection PyTrailingSemicolon,PyPep8
    def write_payload(self, fp: IOWrapper):
        offset = 0
        fp.write_byte(self.flags); offset += 1;
        fp.write_long(self.ttl); offset += 4;
        fp.write_bytes(self.tracing); offset += 25;
        fp.write_byte(len(self.service)); offset += 1;
        fp.write_string(self.service); offset += len(self.service);
        self.headers.write_headers(fp); offset += self.headers.size();
        fp.write_byte(self.csumtype); offset += 1;
        for arg in self.args:
            arg.write_arg(fp); offset += arg.size();
        assert offset == self.get_payload_size()


class CallResFrame(FrameWithArgs, CallFlags):
    """
    flags:1 code:1 tracing:25
    nh:1 (hk~1 hv~1){nh}
    csumtype:1 (csum:4){0,1} arg1~2 arg2~2 arg3~2
    """
    TYPE = 0x04

    def __init__(self):
        FrameWithArgs.__init__(self)
        CallFlags.__init__(self)
        self.code = 0
        self.tracing = bytes(25)
        self.headers = KVHeaders({}, 1)
        self.csumtype = 0

    # noinspection PyPep8
    def read_payload(self, fp: IOWrapper, size: int):
        offset = 0
        self.flags = fp.read_byte("callres.flags"); offset += 1;
        self.code = fp.read_byte("callres.code"); offset += 1;
        self.tracing = fp.read_bytes(25, "callres.tracing"); offset += 25;
        self.headers = KVHeaders.read_kv_headers(fp, 1, "callreq.headers"); offset += self.headers.size();
        self.csumtype = fp.read_byte("callres.csumtype"); offset += 1;
        if self.csumtype != 0:
            raise NotImplementedError("Checksum type not supported")
        self.args = []
        arg_count = 1
        while offset < size:
            arg = Arg.read_arg(fp, offset, size, self.is_more_fragments_follow(), "callres.args[%d]" % arg_count)
            self.args.append(arg); offset += arg.size();
            arg_count += 1

    def get_payload_size(self):
        return (_.flag(1) + _.code(1) + _.tracing(25) +
                self.headers.size() +
                _.csumtype(1) + sum([arg.size() for arg in self.args]))

    # noinspection PyPep8
    def write_payload(self, fp: IOWrapper):
        offset = 0
        fp.write_byte(self.flags); offset += 1;
        fp.write_byte(self.code); offset += 1;
        fp.write_bytes(self.tracing); offset += 25;
        self.headers.write_headers(fp); offset += self.headers.size();
        fp.write_byte(self.csumtype); offset += 1;
        for arg in self.args:
            arg.write_arg(fp); offset += arg.size();
        assert offset == self.get_payload_size()


class FrameContinue(FrameWithArgs, CallFlags):
    """
    flags:1 csumtype:1 (csum:4){0,1} {continuation}
    """
    PREFIX = ""

    def __init__(self):
        FrameWithArgs.__init__(self)
        CallFlags.__init__(self)
        self.csumtype = 0

    # noinspection PyPep8
    def read_payload(self, fp: IOWrapper, size: int):
        offset = 0
        self.flags = fp.read_byte(self.PREFIX + ".flags"); offset += 1;
        self.csumtype = fp.read_byte(self.PREFIX + ".csumtype"); offset += 1;
        if self.csumtype != 0:
            raise NotImplementedError("Checksum type not supported")
        self.args = []
        arg_count = 1
        while offset < size:
            arg = Arg.read_arg(fp, offset, size, self.is_more_fragments_follow(), self.PREFIX + ".args[%d]" % arg_count)
            self.args.append(arg); offset += arg.size();
            arg_count += 1

    def get_payload_size(self):
        return _.flag(1) + _.csumtype(1) + sum([arg.size() for arg in self.args])

    # noinspection PyPep8
    def write_payload(self, fp: IOWrapper):
        offset = 0
        fp.write_byte(self.flags); offset += 1;
        fp.write_byte(self.csumtype); offset += 1;
        for arg in self.args:
            arg.write_arg(fp); offset += arg.size();
        assert offset == self.get_payload_size()


class CallReqContinueFrame(FrameContinue):
    PREFIX = "callreqcontinue"
    TYPE = 0x13


class CallResContinueFrame(FrameContinue):
    PREFIX = "callrescontinue"
    TYPE = 0x14


class ErrorFrame(Frame):
    """
    code:1 tracing:25 message~2
    """
    TYPE = 0xff

    message: str
    tracing: bytes
    code: int

    def __init__(self):
        super().__init__()
        self.code = 0
        self.tracing = bytes(25)
        self.message = ""

    def read_payload(self, fp: IOWrapper, size: int):
        offset = 0
        self.code = fp.read_byte("error.code"); offset += 1;
        self.tracing = fp.read_bytes(25, "error.tracing"); offset += 25;
        message_len = fp.read_short("error.message_len"); offset += 2;
        self.message = fp.read_string(message_len, "error.message"); offset += message_len;
        assert offset == size

    def get_payload_size(self):
        return _.code(1) + _.tracing(25) + _.message_len(2) + len(self.message)

    def write_payload(self, fp: IOWrapper):
        offset = 0
        fp.write_byte(self.code); offset += 1;
        fp.write_bytes(self.tracing); offset += 25;
        fp.write_short(len(self.message)); offset += 2;
        fp.write_string(self.message); offset += len(self.message)
