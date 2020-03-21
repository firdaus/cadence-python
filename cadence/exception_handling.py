import json
import logging
import traceback

import tblib

THIS_SOURCE = "cadence-python"

logger = logging.getLogger(__name__)


class ExternalException(Exception):
    def __init__(self, details):
        super().__init__(details)

    @property
    def details(self):
        return self.args[0]


def exception_class_fqn(o):
    # Copied from: https://stackoverflow.com/a/2020083
    module = o.__class__.__module__
    if module is None or module == str.__class__.__module__:
        return o.__class__.__name__  # Avoid reporting __builtin__
    else:
        return module + '.' + o.__class__.__name__


def import_class_from_string(path):
    # Taken from: https://stackoverflow.com/a/30042585
    from importlib import import_module
    module_path, _, class_name = path.rpartition('.')
    mod = import_module(module_path)
    klass = getattr(mod, class_name)
    return klass


def serialize_exception(ex: Exception):
    exception_cls_name: str = exception_class_fqn(ex)
    tb = "".join(traceback.format_exception(type(ex), ex, ex.__traceback__))
    details = json.dumps({
        "class": exception_cls_name,
        "args": ex.args,
        "traceback": tb,
        "source": THIS_SOURCE
    })
    return details


def deserialize_exception(details) -> Exception:
    """
    TODO: Support built-in types like Exception
    """
    exception: Exception = None
    details_dict = json.loads(details)
    source = details_dict.get("source")
    exception_cls_name: str = details_dict.get("class")

    if source == THIS_SOURCE and exception_cls_name:
        try:
            klass = import_class_from_string(exception_cls_name)
            exception = klass(*details_dict["args"])
            t = tblib.Traceback.from_string(details_dict["traceback"])
            exception.with_traceback(t.as_traceback())
        except Exception as e:
            exception = None
            logger.error("Failed to deserialize exception (details=%s) cause=%r", details_dict, e)

    if not exception:
        return ExternalException(details_dict)
    else:
        return exception
