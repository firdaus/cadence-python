from select import select
from socket import socket
from typing import IO, Callable


class IOWrapper:
    def __init__(self, io_stream: IO, socket_: socket = None):
        self.io_stream = io_stream
        self.socket = socket_
        self.next_timeout_cb = None

    def set_next_timeout_cb(self, cb: Callable):
        self.next_timeout_cb = cb

    def read_or_eof(self, size, field):
        if self.next_timeout_cb and self.socket:
            timeout = self.socket.gettimeout()
            self.socket.setblocking(False)
            while True:
                ready_to_read, _, _ = select([self.socket], [], [], 1)
                if ready_to_read:
                    break
                else:
                    self.next_timeout_cb()
            self.next_timeout_cb = None
            self.socket.setblocking(True)
            self.socket.settimeout(timeout)
        buf: bytes = self.io_stream.read(size)
        if len(buf) != size:
            raise EOFError(field)
        return buf

    def read_short(self, field: str) -> int:
        return int.from_bytes(self.read_or_eof(2, field), byteorder='big', signed=False)

    def read_long(self, field: str) -> int:
        return int.from_bytes(self.read_or_eof(4, field), byteorder='big', signed=False)

    def read_byte(self, field: str) -> int:
        return int.from_bytes(self.read_or_eof(1, field), byteorder='big', signed=False)

    def read_bytes(self, n: int, field: str) -> bytes:
        buf: bytes = self.read_or_eof(n, field)
        return buf

    def read_string(self, n: int, field: str) -> str:
        buf: bytes = self.read_or_eof(n, field)
        return str(buf, "utf-8")

    def write_short(self, v: int):
        self.io_stream.write(v.to_bytes(2, byteorder='big', signed=False))

    def write_long(self, v: int):
        self.io_stream.write(v.to_bytes(4, byteorder='big', signed=False))

    def write_byte(self, v: int):
        self.io_stream.write(v.to_bytes(1, byteorder='big', signed=False))

    def write_bytes(self, b: bytes):
        self.io_stream.write(b)

    def write_string(self, s: str):
        self.io_stream.write(bytes(s, "utf-8"))

    def flush(self):
        self.io_stream.flush()

    def close(self):
        self.io_stream.close()
