import os
import typing
from enum import EnumMeta

primitives = [str, int, bytes, bool, float]


def json_to_data_class(value, cls):
    if type(value) in primitives:
        return value
    elif value is None:
        return None
    elif isinstance(cls, EnumMeta):
        return cls.value_for(value)
    elif "List[" in str(cls):
        l = []
        for v in value:
            l.append(json_to_data_class(v, cls.__args__[0]))
        return l
    elif "Dict[" in str(cls):
        d = {}
        value_type = cls.__args__[1]
        for k, v in value:
            d[k] = json_to_data_class(v, value_type)
        return d
    else:
        assert isinstance(value, dict)
        obj = cls()
        hints = typing.get_type_hints(cls)
        for k, v in value.items():
            value_type = hints.get(k)
            setattr(obj, k, json_to_data_class(v, value_type))
        return obj
