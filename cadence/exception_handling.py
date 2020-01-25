import json
import logging
from typing import Dict

import tblib

THIS_SOURCE = "cadence-python"

logger = logging.getLogger(__name__)


class ExternalException(Exception):
    def __init__(self, reason, details):
        super().__init__(reason, details)

    @property
    def reason(self):
        return self.args[0]

    @property
    def details(self):
        return self.args[1]


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


def serialize_exception(ex):
    reason: str = exception_class_fqn(ex)
    traceback: Dict = tblib.Traceback(ex.__traceback__).to_dict()
    details = json.dumps({
        "repr": repr(ex),
        "traceback": traceback,
        "source": THIS_SOURCE
    })
    return reason, details


def deserialize_exception(reason, details) -> Exception:
    details = json.loads(details)
    source = details.get("source")
    exception: Exception = None

    if source == THIS_SOURCE:
        try:
            klass = import_class_from_string(reason)
            r: str = details["repr"]
            args = r[r.index("("):]
            exception = eval("klass" + args)
            traceback = tblib.Traceback.from_dict(details["traceback"])
            exception.with_traceback(traceback.as_traceback())
        except Exception as e:
            exception = None
            logger.error("Failed to deserialize exception (reason=%s details=%s) cause=%r", reason, details, e)

    if not exception:
        return ExternalException(reason, details)
    else:
        return exception
