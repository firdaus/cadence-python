import os
from io import BytesIO
from unittest import TestCase

from cadence.frames import ErrorFrame
from ..ioutils import IOWrapper
from ..frames import Frame, InitReqFrame, FrameHeader, InitResFrame, CallReqFrame, CallResFrame, \
    CallReqContinueFrame
from ..kvheaders import KVHeaders

SAMPLE_FRAME_HEADER = bytes.fromhex("""
00 46 
01 
00 
00 00 00 00 
00 00 00 00 00 00 00 00""")

__location__ = os.path.dirname(__file__)


SAMPLE_KVHEADERS = bytes.fromhex(
    "00 02"                                # (nh)
    "00 09"                                # (key-length)
    "68 6f 73 74 5f 70 6f 72 74"           # (key) - "host_port"
    "00 09"                                # (value-length)
    "30 2e 30 2e 30 2e 30 3a 30"           #(value) - "0.0.0.0:0"
    "00 0c"                                # (key-length)  12
    "70 72 6f 63 65 73 73 5f 6e 61 6d 65"  # (key) - "process_name"
    "00 0c"                                # (value-length) - 12 
    "6a 61 76 61 2d 70 72 6f 63 65 73 73"  # (value)  "java-process"
)

SAMPLE_INITREQ = bytes.fromhex(
    "00 46"                                # (size - entire frame, including body)
    "01"                                   # (type) - init req
    "00"                                   # (reserved)
    "00 00 00 00"                          # (id)
    "00 00 00 00 00 00 00 00"              # (reserved)
    "00 02"                                # (version)
    "00 02"                                # (nh)
    "00 09"                                # (key-length)
    "68 6f 73 74 5f 70 6f 72 74"           # (key) - "host_port"
    "00 09"                                # (value-length)
    "30 2e 30 2e 30 2e 30 3a 30"           # (value) - "0.0.0.0:0"
    "00 0c"                                # (key-length) - 12
    "70 72 6f 63 65 73 73 5f 6e 61 6d 65"  # (key) - "process_name"
    "00 0c"                                # (value-length) - 12
    "6a 61 76 61 2d 70 72 6f 63 65 73 73"  # (value) - "java-process"
)

SAMPLE_INITRES = bytes.fromhex(
    "00 a8"                                # (size)
    "02"                                   # (type) - init response
    "00"                                   # (reserved)
    "00 00 00 00"                          # (id)
    "00 00 00 00 00 00 00 00"              # (reserved)
    "00 02"                                # (version)
    "00 05"                                # (nh)
    "00 10"                                # (key-length) 16
    "74 63 68 61 6e 6e 65 6c 5f"           # (key) - "tchannel_version"
        "76 65 72 73 69 6f 6e"     
    "00 06"                                # (value-length)
    "31 2e 31 31 2e 30"                    # (value) - "1.11.0"
    "00 09"                                # (key-length)
    "68 6f 73 74 5f 70 6f 72 74"           # (key) - "host_port"
    "00 0e"                                # (value-length)
    "31 32 37 2e 30 2e 30 2e 31 3a 37 39"  # (value) - "127.0.0.1:7933"
        "33 33"
    "00 0c"                                # (key-length)
    "70 72 6f 63 65 73 73 5f 6e 61 6d 65"  # (key) - "process_name"
    "00 15"                                # (value-length)
    "63 61 64 65 6e 63 65 2d 73 65 72 76"  # (value) - "cadence-server[14479]"
        "65 72 5b 31 34 34 37 39 5d"                                                                                 
    "00 11"                                # (key-length)
    "74 63 68 61 6e 6e 65 6c 5f 6c 61 6e"  # (key) - "tchannel_language"
        "67 75 61 67 65"                                                                   
    "00 02"                                # (value-length)
    "67 6f"                                # (value) - "go"
    "00 19"                                # (key-length)
    "74 63 68 61 6e 6e 65 6c 5f 6c 61 6e"  # (key) - "tchannel_language_version"
        "67 75 61 67 65 5f 76 65 72 73 69" 
        "6f 6e"                                                      
    "00 06"                                # (value-length)
    "31 2e 31 32 2e 34"                    # (value) - "1.12.4"
)

SAMPLE_CALLREQ = bytes.fromhex(
    "01 8a"                                # (size)
    "03"                                   # (type) - call req
    "00"                                   # (reserved)
    "00 00 00 01"                          # (id)
    "00 00 00 00 00 00 00 00"              # (reserved)
    "00"                                   # (flags)
    "00 00 03 e8"                          # (ttl)
    "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00"  # (tracing)
    "10"                                               # (service-length)
    "63 61 64 65 6e 63 65 2d 66 72 6f 6e 74 65 6e 64"  # (service) - "cadence-frontend"
    "03"                                               # (nh)
    "02"                                               # (header-key-length)
    "61 73"                                            # (header-key) "as" - The arg scheme
    "06"                                               # (header-value-length)
    "74 68 72 69 66 74"                                # (header-value) "thrift"
    "02"                                               # (header-key-length)
    "72 65"                                            # (header-key) - "re" - retry flags
    "01"                                               # (value-length)
    "63"                                               # (value) - "c"
    "02"                                               # (header-key-length)
    "63 6e"                                            # (header-key) - "cn" - Caller Name
    "0e"                                               # (value-length)
    "63 61 64 65 6e 63 65 2d 63 6c 69 65 6e 74"        # (value) - "cadence-client"
    "00"                                               # (csum type) - none
    "00 27"                                            # (arg1-length) - method name
    "57 6f 72 6b 66 6c 6f 77 53 65 72 76 69 63 65"     # (arg-1) - "WorkflowService::StartWorkflowExecution"
    "3a 3a 53 74 61 72 74 57 6f 72 6b 66 6c 6f 77"
    "45 78 65 63 75 74 69 6f 6e" 
    "00 38"                                            # (arg2-length) - application headers
    "00 02"                                            # (nh)
    "00 09"                                            # (key-length)
    "75 73 65 72 2d 6e 61 6d 65"                       # (key) - "user-name"
    "00 07"                                            # (value-length)
    "66 69 72 64 61 75 73"                             # (value) - "firdaus"
    "00 09"                                            # (key-length)
    "68 6f 73 74 2d 6e 61 6d 65"                       # (key) - "host-name"
    "00 15"                                            # (value-length)
    "66 69 72 64 61 75 73 2d 6d 61 63 62 6f 6f 6b "    # (value) - "firdaus-macbook.local"
    "2e 6c 6f 63 61 6c" 
    "00 c3"                                            # (arg-length) - thrift payload
    "0c 00 01 0b 00 0a 00 00 00 0b 74 65 73 74 2d "    # (thrift-payload)
    "64 6f 6d 61 69 6e 0b 00 14 00 00 00 24 65 62 "
    "30 37 63 32 39 64 2d 35 33 35 35 2d 34 65 61 "
    "65 2d 38 33 34 39 2d 34 66 61 62 61 39 35 32 "
    "63 33 64 38 0c 00 1e 0b 00 0a 00 00 00 0d 74 "
    "65 73 74 2d 77 6f 72 6b 66 6c 6f 77 00 0c 00 "
    "28 0b 00 0a 00 00 00 0d 74 65 73 74 2d 74 61 "
    "73 6b 6c 69 73 74 08 00 14 00 00 00 00 00 0b "
    "00 32 00 00 00 0a 00 00 00 00 00 00 00 00 00 "
    "00 08 00 3c 00 09 3a 80 08 00 46 00 00 00 0a "
    "0b 00 5a 00 00 00 24 65 37 35 30 61 61 36 61 "
    "2d 64 64 33 63 2d 34 64 34 63 2d 62 38 36 65 "
    "2d 64 35 38 34 64 38 66 66 61 65 63 32 00 00 "
)

SAMPLE_CALLRES = bytes.fromhex(
    "00 90"                                           # (size)
    "04"                                              # (type) - call res
    "00"                                              # (reserved)
    "00 00 00 01"                                     # (id)
    "00 00 00 00 00 00 00 00"                         # (reserved)
    "00"                                              # (flags)
    "00"                                              # (code)
    "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 "   # (tracing)
    "00 00 00 00 00 00 00 00 00 00" 
    "01"                                              # (nh)
    "02"                                              # (key-length)
    "61 73"                                           # (key) - "as"
    "06"                                              # (value-length)
    "74 68 72 69 66 74"                               # (value) - "thrift"
    "00"                                              # (csumtype)
    "00 00"                                           # arg1 length - method name
    "00 23"                                           # (arg2 length)
        "00 01"                                       # (nh)
        "00 0d"                                       # (key-length)
        "24 72 70 63 24 2d 73 65 72 76 69 63 65"      # (key) - "$rpc$-service"
        "00 10"                                       # (value-length)
        "63 61 64 65 6e 63 65 2d 66 72 6f 6e 74 65 "  # (value) - "cadence-frontend"
        "6e 64"
    "00 30"                                           # (arg3-length) thrift payload
    "0c 00 00 0b 00 0a 00 00 00 24 61 30 37 36 39 "   # (arg3 value)
    "61 33 65 2d 35 63 38 35 2d 34 35 34 61 2d 61 "
    "30 33 31 2d 33 31 34 34 35 32 62 63 66 63 64 "
    "65 00 00"
)

SAMPLE_ERROR = bytes.fromhex(
    "00 90"                                           # (size)
    "ff"                                              # (type)
    "00"                                              # (reserved)
    "00 00 00 01"                                     # (id)
    "00 00 00 00 00 00 00 00"                         # (reserved) 
    "05"                                              # (code) - UNEXPECTED_ERROR
    "00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 "   # (tracing)
    "00 00 00 00 00 00 00 00 00 00" 
    "00 64"                                           # (message_len)
    "43 61 64 65 6e 63 65 20 69 6e 74 65 72 6e 61 "   # (message)
    "6c 20 65 72 72 6f 72 2c 20 6d 73 67 3a 20 47 "   # "Cadence internal error, msg: GetDomain operation"
    "65 74 44 6f 6d 61 69 6e 20 6f 70 65 72 61 74 "   # "failed. Error gocql: no hosts available in the pool"
    "69 6f 6e 20 66 61 69 6c 65 64 2e 20 45 72 72 "
    "6f 72 20 67 6f 63 71 6c 3a 20 6e 6f 20 68 6f "
    "73 74 73 20 61 76 61 69 6c 61 62 6c 65 20 69 "
    "6e 20 74 68 65 20 70 6f 6f 6c"
)


class DummyFrame(Frame):
    VERSION = 2
    TYPE = 0x01

    def __init__(self, dummy_payload_size):
        super().__init__()
        self.dummy_payload_size = dummy_payload_size

    def get_payload_size(self):
        return self.dummy_payload_size

    def read_payload(self, fp: IOWrapper, size: int):
        pass

    def write_payload(self, fp: IOWrapper):
        pass


class TestReadHeader(TestCase):

    def test_read_header(self):
        fp = BytesIO(SAMPLE_FRAME_HEADER)
        header: FrameHeader = FrameHeader.read_header(IOWrapper(fp))
        self.assertEqual(0x01, header.payload_type)
        fp.close()


class TestWriteHeader(TestCase):

    def test_write_header(self):
        frame = DummyFrame(0x46 - 16)
        frame.id = 0
        fp = IOWrapper(BytesIO())
        frame.write_header(fp)
        self.assertEqual(SAMPLE_FRAME_HEADER, fp.fp.getvalue())


class TestReadShort(TestCase):
    def test_read_short(self):
        fp = IOWrapper(BytesIO(bytes.fromhex("01F4")))
        self.assertEqual(500, fp.read_short("dummy"))

    def test_read_short_fail(self):
        fp = IOWrapper(BytesIO(bytes.fromhex("0001")))
        self.assertNotEqual(500, fp.read_short("dummy"))

    def test_eof(self):
        with self.assertRaises(EOFError):
            fp = IOWrapper(BytesIO(bytes.fromhex("01")))
            fp.read_short("dummy")

    def test_boundary(self):
        fp = IOWrapper(BytesIO(bytes.fromhex("FFFF")))
        self.assertEqual(0xFFFF, fp.read_short("dummy"))


class TestReadOrEof(TestCase):
    def test_read_all(self):
        fp = IOWrapper(BytesIO(bytes.fromhex("0001")))
        buf = fp.read_or_eof(2, "dummy")
        self.assertEqual(2, len(buf))
        with self.assertRaises(EOFError):
            fp.read_or_eof(2, "dummy")

    def test_read_partial(self):
        fp = IOWrapper(BytesIO(bytes.fromhex("0001")))
        buf = fp.read_or_eof(1, "dummy")
        self.assertEqual(1, len(buf))

    def test_read_empty(self):
        fp = IOWrapper(BytesIO())
        with self.assertRaises(EOFError):
            fp.read_or_eof(2, "dummy")

    def test_read_pass_eof(self):
        fp = IOWrapper(BytesIO(bytes.fromhex("0001")))
        with self.assertRaises(EOFError):
            fp.read_or_eof(4, "dummy")

    def test_eof_error_contains_field(self):
        fp = IOWrapper(BytesIO())
        with self.assertRaisesRegex(EOFError, "dummy"):
            fp.read_or_eof(2, "dummy")


class TestKVHeaders(TestCase):
    def test_read(self):
        header: KVHeaders = KVHeaders.read_kv_headers(IOWrapper(BytesIO(SAMPLE_KVHEADERS)), 2, "kvheaders")
        self.assertEqual("0.0.0.0:0", header.d['host_port'])
        self.assertEqual("java-process", header.d['process_name'])

    def test_header_size(self):
        header: KVHeaders = KVHeaders.read_kv_headers(IOWrapper(BytesIO(SAMPLE_KVHEADERS)), 2, "kvheaders")
        self.assertEqual(len(BytesIO(SAMPLE_KVHEADERS).getvalue()), header.size())

    def test_header_write(self):
        header: KVHeaders = KVHeaders.read_kv_headers(IOWrapper(BytesIO(SAMPLE_KVHEADERS)), 2, "kvheaders")
        fp = IOWrapper(BytesIO())
        header.write_headers(fp)
        self.assertEqual(SAMPLE_KVHEADERS, fp.fp.getvalue())


class TestInitReqFrame(TestCase):
    def test_read_write(self):
        frame: Frame = Frame.read_frame(IOWrapper(BytesIO(SAMPLE_INITREQ)))
        self.assertEqual(0x01, frame.TYPE)
        # noinspection PyTypeChecker
        frame: InitReqFrame = frame
        self.assertEqual(0, frame.id)
        self.assertEqual(2, len(frame.headers.d))
        self.assertEqual("0.0.0.0:0", frame.headers.d['host_port'])
        self.assertEqual("java-process", frame.headers.d['process_name'])

        buf = BytesIO()
        frame.write(IOWrapper(buf))
        self.assertEqual(SAMPLE_INITREQ, buf.getvalue())


class TestInitResFrame(TestCase):
    def test_read_write(self):
        frame: Frame = Frame.read_frame(IOWrapper(BytesIO(SAMPLE_INITRES)))
        self.assertEqual(0x02, frame.TYPE)
        # noinspection PyTypeChecker
        frame: InitResFrame = frame
        self.assertEqual(0, frame.id)
        self.assertEqual(5, len(frame.headers.d))
        self.assertEqual("1.11.0", frame.headers.d['tchannel_version'])
        self.assertEqual("127.0.0.1:7933", frame.headers.d['host_port'])
        self.assertEqual("cadence-server[14479]", frame.headers.d['process_name'])
        self.assertEqual("go", frame.headers.d['tchannel_language'])
        self.assertEqual("1.12.4", frame.headers.d['tchannel_language_version'])

        buf = BytesIO()
        frame.write(IOWrapper(buf))
        self.assertEqual(SAMPLE_INITRES, buf.getvalue())


class TestCallReqFrame(TestCase):
    def test_read_write(self):
        frame: Frame = Frame.read_frame(IOWrapper(BytesIO(SAMPLE_CALLREQ)))
        self.assertEqual(0x03, frame.TYPE)
        frame: CallReqFrame = frame
        self.assertEqual(1, frame.id)
        self.assertEqual(0, frame.flags)
        self.assertEqual(0x3e8, frame.ttl)
        self.assertEqual(25, len(frame.tracing))
        self.assertEqual("cadence-frontend", frame.service)
        self.assertEqual(3, len(frame.headers.d))
        self.assertEqual("thrift", frame.headers.d['as'])
        self.assertEqual("c", frame.headers.d['re'])
        self.assertEqual("cadence-client", frame.headers.d['cn'])
        self.assertEqual(0, frame.csumtype)
        self.assertEqual(3, len(frame.args))
        self.assertEqual(False, frame.args[0].is_fragment)
        self.assertEqual(0x27, len(frame.args[0].buf))
        self.assertEqual(False, frame.args[1].is_fragment)
        self.assertEqual(0x38, len(frame.args[1].buf))
        self.assertEqual(False, frame.args[2].is_fragment)
        self.assertEqual(0xc3, len(frame.args[2].buf))

        b = BytesIO()
        frame.write(IOWrapper(b))
        self.assertEqual(SAMPLE_CALLREQ, b.getvalue())


class TestCallResFrame(TestCase):
    def test_read_write(self):
        frame: Frame = Frame.read_frame(IOWrapper(BytesIO(SAMPLE_CALLRES)))
        self.assertEqual(0x04, frame.TYPE)
        frame: CallResFrame = frame
        self.assertEqual(1, frame.id)
        self.assertEqual(0, frame.flags)
        self.assertEqual(0, frame.code)
        self.assertEqual(25, len(frame.tracing))
        self.assertEqual(1, len(frame.headers.d))
        self.assertEqual("thrift", frame.headers.d['as'])
        self.assertEqual(0, frame.csumtype)
        self.assertEqual(3, len(frame.args))
        self.assertEqual(False, frame.args[0].is_fragment)
        self.assertEqual(0x0, len(frame.args[0].buf))
        self.assertEqual(False, frame.args[1].is_fragment)
        self.assertEqual(0x23, len(frame.args[1].buf))
        self.assertEqual(False, frame.args[2].is_fragment)
        self.assertEqual(0x30, len(frame.args[2].buf))

        b = BytesIO()
        frame.write(IOWrapper(b))
        self.assertEqual(SAMPLE_CALLRES, b.getvalue())


class TestContinuation(TestCase):
    def test_read_continue(self):
        with open(os.path.join(__location__, "callreq-fragments.txt")) as fp:
            dump = fp.read()
        fp: BytesIO = BytesIO(bytes.fromhex(dump))
        frame: CallReqFrame = Frame.read_frame(IOWrapper(fp))
        self.assertEqual(CallReqFrame.TYPE, frame.TYPE)
        self.assertEqual(1, frame.id)
        self.assertEqual(True, frame.is_more_fragments_follow())
        self.assertEqual(False, frame.args[0].is_fragment)
        self.assertEqual(False, frame.args[1].is_fragment)
        self.assertEqual(True, frame.args[2].is_fragment)

        frame: CallReqContinueFrame = Frame.read_frame(IOWrapper(fp))
        self.assertEqual(CallReqContinueFrame.TYPE, frame.TYPE)
        self.assertEqual(1, frame.id)
        self.assertEqual(False, frame.is_more_fragments_follow())
        self.assertEqual(1, len(frame.args))
        self.assertEqual(False, frame.args[0].is_fragment)


class TestErrorFrame(TestCase):
    def test_read_write(self):
        frame: Frame = Frame.read_frame(IOWrapper(BytesIO(SAMPLE_ERROR)))
        self.assertEqual(0xff, frame.TYPE)
        frame: ErrorFrame = frame
        self.assertEqual(1, frame.id)
        self.assertEqual(5, frame.code)
        self.assertEqual(
            "Cadence internal error, msg: GetDomain operation failed. Error gocql: no hosts available in the pool",
            frame.message)

        b = BytesIO()
        frame.write(IOWrapper(b))
        self.assertEqual(SAMPLE_ERROR, b.getvalue())
