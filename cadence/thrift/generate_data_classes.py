import json
import os
import re
from jinja2 import Template, Environment

TYPE_MAP = {
    'string': 'str',
    'i32': 'int',
    'i64': 'int',
    'binary': 'bytes',
    'bool': 'bool',
    'double': 'float'
}

HEADER = """from __future__ import annotations
from typing import List, Dict
from dataclasses import dataclass, field
from enum import IntEnum

"""

DATA_CLASS_TEMPLATE = """
# noinspection PyPep8
@dataclass
class {{type_name}}:
    {% for field in fields %}{{field.name|to_snake()}}: {{ field.type|python_type }} = {{field.type|python_value}}
    {%else%}pass
    {% endfor %}

"""

ENUM_TEMPLATE = """
class {{type_name}}(IntEnum):
    {% for item in items %}{{item.name}} = {{loop.index0}}
    {% endfor %}
    @classmethod
    def value_for(cls, n: int) -> {{type_name}}:
        return next(filter(lambda i: i == n, cls), None)

    
"""

def filter_to_snake(value):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', value)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def python_type(thrift_type):
    if isinstance(thrift_type, dict):
        if thrift_type['name'] == "list":
            return 'List[%s]' % python_type(thrift_type['valueType'])
        elif thrift_type['name'] == "map":
            return 'Dict[%s, %s]' % (python_type(thrift_type['keyType']), python_type(thrift_type['valueType']))
    t = TYPE_MAP.get(thrift_type, None)
    if t: return t
    return thrift_type


def python_value(thrift_type):
    if isinstance(thrift_type, dict):
        if thrift_type['name'] == "list":
            return "field(default_factory=list)"
        elif thrift_type['name'] == "map":
            return "field(default_factory=dict)"
    return "None"


env = Environment()
env.filters['to_snake'] = filter_to_snake
env.filters['python_type'] = python_type
env.filters['python_value'] = python_value


def generate_data_class(type_name, fields):
    template = env.from_string(DATA_CLASS_TEMPLATE)
    return template.render(type_name=type_name, fields=fields, TYPE_MAP=TYPE_MAP)


def generate_enum(type_name, items):
    template = env.from_string(ENUM_TEMPLATE)
    return template.render(type_name=type_name, items=items)


def main():
    this_dir = os.path.dirname(__file__)
    thrift_idl_json_file = os.path.join(this_dir, "shared.json")
    with open(thrift_idl_json_file) as f:
        ast = json.loads(f.read())

    buf = HEADER
    for type_name, fields in ast['exception'].items():
        buf += generate_data_class(type_name, fields)

    for type_name, fields in ast['enum'].items():
        buf += generate_enum(type_name, fields['items'])

    for type_name, fields in ast['struct'].items():
        buf += generate_data_class(type_name, fields)

    print(buf.strip())


if __name__  == '__main__':
    main()
