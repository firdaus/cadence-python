import typing
import re
from enum import Enum
import cadence.types

PRIMITIVES = [int, str, bytes, float, bool]


def camel_to_snake(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def copy_thrift_to_py(thrift_object):
    python_cls = get_python_type(type(thrift_object))
    if python_cls == list:
        obj = []
        for item in thrift_object:
            obj.append(copy_thrift_to_py(item))
    elif python_cls == dict:
        raise NotImplementedError("Thrift dict to Python dict")
    else:
        hints = typing.get_type_hints(python_cls)
        obj = python_cls()
        for thrift_field in dir(thrift_object):
            python_field = camel_to_snake(thrift_field)
            if python_field not in hints:
                continue
            field_type = hints[python_field]
            value = getattr(thrift_object, thrift_field)
            if not value:
                continue
            if field_type in PRIMITIVES:
                setattr(obj, python_field, value)
            elif issubclass(field_type, Enum):
                setattr(obj, python_field, field_type.value_for(value))
            else:
                setattr(obj, python_field, copy_thrift_to_py(value))
    return obj


# sometimes workflow_id maps to either workflowId or workflowID
def last_char_upper(s: str):
    return s[:-1] + s[-1:].upper()


def copy_py_to_thrift(python_object):
    thrift_cls = get_thrift_type(type(python_object))
    thrift_object = thrift_cls()
    for python_field, field_type in typing.get_type_hints(type(python_object)).items():
        value = getattr(python_object, python_field)
        if not value:
            continue
        thrift_field = snake_to_camel(python_field)
        if field_type in PRIMITIVES:
            if hasattr(thrift_object, thrift_field):
                setattr(thrift_object, thrift_field, value)
            elif hasattr(thrift_object, last_char_upper(thrift_field)):
                setattr(thrift_object, last_char_upper(thrift_field), value)
        elif issubclass(field_type, Enum):
            setattr(thrift_object, thrift_field, value.value)
        else:
            # Special handling for case of inconsistent naming in shared.thrift
            # StartTimeFilter StartTimeFilter
            if python_field == "start_time_filter":
                thrift_field = "StartTimeFilter"
            setattr(thrift_object, thrift_field, copy_py_to_thrift(value))
    return thrift_object


def snake_to_camel(snake_str):
    components = snake_str.split('_')
    # We capitalize the first letter of each component except the first one
    # with the 'title' method and join them together.
    return components[0] + ''.join(x.title() for x in components[1:])


def get_thrift_type(python_cls: type) -> type:
    from cadence.thrift import cadence
    thrift_cls = getattr(cadence.shared, python_cls.__name__, None)
    assert thrift_cls, "Thrift class not found: " + python_cls.__name__
    return thrift_cls


def get_python_type(thrift_class: type) -> type:
    if thrift_class == list:
        return list
    elif thrift_class == dict:
        return dict
    else:
        python_cls = getattr(cadence.types, thrift_class.__name__, None)
        assert python_cls, "Python class not found: " + thrift_class.__name__
        return python_cls
