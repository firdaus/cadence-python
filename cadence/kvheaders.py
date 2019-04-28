from __future__ import annotations
from .ioutils import IOWrapper


class KVHeaders:
    @classmethod
    def read_kv_headers(cls, fp: IOWrapper, len_size, field: str) -> KVHeaders:
        if len_size == 2:
            fn = fp.read_short
        elif len_size == 1:
            fn = fp.read_byte
        nh = fn(field + "." + "nh")
        d = {}
        for i in range(nh):
            key_len = fn("field[%d].key_len" % (i + 1))
            key = fp.read_string(key_len, "field[%d].key" % (i + 1))
            value_len = fn("field[%d].value_len" % (i + 1))
            value = fp.read_string(value_len, "field[%d].value" % (i + 1))
            d[key] = value
        return KVHeaders(d, len_size)

    def __init__(self, d=None, len_size=2):
        if not d:
            d = {}
        self.d = d
        self.len_size = len_size

    def write_headers(self, fp: IOWrapper):
        if self.len_size == 2:
            fn = fp.write_short
        elif self.len_size == 1:
            fn = fp.write_byte
        fn(len(self.d))
        for key, value in self.d.items():
            fn(len(key))
            fp.write_string(key)
            fn(len(value))
            fp.write_string(value)

    def size(self):
        return self.len_size + (self.len_size * len(self.d) * 2) + sum([len(k) for k in self.d.keys()]) + sum(
            [len(v) for v in self.d.values()])
