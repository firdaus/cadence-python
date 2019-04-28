from typing import IO


class IOWrapper:
    fp: IO

    def __init__(self, fp: IO):
        self.fp = fp

    def read_or_eof(self, size, field):
        buf: bytes = self.fp.read(size)
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
        self.fp.write(v.to_bytes(2, byteorder='big', signed= False))

    def write_long(self, v: int):
        self.fp.write(v.to_bytes(4, byteorder='big', signed=False))

    def write_byte(self, v: int):
        self.fp.write(v.to_bytes(1, byteorder='big', signed=False))

    def write_bytes(self, b: bytes):
        self.fp.write(b)

    def write_string(self, s: str):
        self.fp.write(bytes(s, "utf-8"))

    def flush(self):
        self.fp.flush()
