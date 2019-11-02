import json
import typing
import inspect
import re
from enum import Enum, IntEnum
import cadence.cadence_types
from cadence.thrift import cadence_thrift

PRIMITIVES = [int, str, bytes, float, bool]


def camel_to_snake(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def copy_thrift_to_py(thrift_object, field_type=None):
    if thrift_object is None:
        obj = None
    elif field_type and field_type in PRIMITIVES:
        obj = thrift_object
    elif field_type and inspect.isclass(field_type) and issubclass(field_type, Enum):
        obj = field_type.value_for(thrift_object)
    elif type(thrift_object) == list:
        assert field_type
        obj = []
        for item in thrift_object:
            obj.append(copy_thrift_to_py(item, field_type=field_type.__args__[0]))
    elif type(thrift_object) == dict:
        assert field_type
        obj = {}
        assert isinstance(thrift_object, dict)
        for key, value in thrift_object.items():
            obj[key] = copy_thrift_to_py(value, field_type=field_type.__args__[1])
    else:
        python_cls = get_python_type(type(thrift_object))
        hints = typing.get_type_hints(python_cls)
        obj = python_cls()
        for thrift_field in dir(thrift_object):
            python_field = camel_to_snake(thrift_field)
            if python_field not in hints:
                continue
            field_type = hints[python_field]
            value = getattr(thrift_object, thrift_field)
            python_value = copy_thrift_to_py(value, field_type)
            if python_value is not None:  # retain default value in object in the case of list and dict
                setattr(obj, python_field, python_value)
    return obj


# sometimes workflow_id maps to either workflowId or workflowID
def last_char_upper(s: str):
    return s[:-1] + s[-1:].upper()


def copy_py_to_thrift(python_object, field_type=None):
    if python_object is None:
        thrift_object = None
    elif field_type and field_type in PRIMITIVES:
        thrift_object = python_object
    elif type(python_object) == list:
        thrift_object = []
        for item in python_object:
            thrift_object.append(copy_py_to_thrift(item, field_type=field_type.__args__[0]))
    elif type(python_object) == dict:
        thrift_object = {}
        assert isinstance(python_object, dict)
        assert field_type
        for key, value in python_object.items():
            thrift_object[key] = copy_py_to_thrift(value, field_type=field_type.__args__[1])
    elif field_type and inspect.isclass(field_type) and issubclass(field_type, IntEnum):
        if python_object is None:
            thrift_object = None
        else:
            assert isinstance(python_object, IntEnum)
            thrift_object = python_object.value
    else:
        thrift_cls = get_thrift_type(type(python_object))
        thrift_object = thrift_cls()
        for python_field, field_type in typing.get_type_hints(type(python_object)).items():
            value = getattr(python_object, python_field)
            thrift_field = snake_to_camel(python_field)
            # Special handling for case of inconsistent naming in shared.thrift
            # StartTimeFilter StartTimeFilter
            if python_field == "start_time_filter":
                thrift_field = "StartTimeFilter"
            elif python_field == "history_event_filter_type":
                thrift_field = "HistoryEventFilterType"
            thrift_value = copy_py_to_thrift(value, field_type)
            if hasattr(thrift_object, thrift_field):
                setattr(thrift_object, thrift_field, thrift_value)
            elif hasattr(thrift_object, last_char_upper(thrift_field)):
                setattr(thrift_object, last_char_upper(thrift_field), thrift_value)
    return thrift_object


def snake_to_camel(snake_str):
    components = snake_str.split('_')
    # We capitalize the first letter of each component except the first one
    # with the 'title' method and join them together.
    return components[0] + ''.join(x.title() for x in components[1:])


def get_thrift_type(python_cls: type) -> type:
    thrift_cls = getattr(cadence_thrift.shared, python_cls.__name__, None)
    assert thrift_cls, "Thrift class not found: " + python_cls.__name__
    return thrift_cls


def get_python_type(thrift_class: type) -> type:
    python_cls = getattr(cadence.cadence_types, thrift_class.__name__, None)
    assert python_cls, "Python class not found: " + thrift_class.__name__
    return python_cls


def args_to_json(args: list) -> str:
    if args is None or len(args) == 0:
        return json.dumps(None)
    elif len(args) == 1:
        return json.dumps(args[0])
    else:
        return json.dumps(args)


def json_to_args(jsonb: bytes) -> typing.Optional[list]:
    parsed = json.loads(jsonb)
    if parsed is None:
        return []
    elif isinstance(parsed, list):
        return parsed
    else:
        return [parsed]
