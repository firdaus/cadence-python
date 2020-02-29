import inspect
import logging
import logging.config

from cadence.tests.interceptor_testing_utils import LOGGING, get_counter_filter_counter, reset_counter_filter_counter

a_captured = None
b_captured = None
args_captured = None
kwargs_captured = None


class Target:
    def do_stuff(self, a, b=2):
        global a_captured, b_captured
        a_captured = a
        b_captured = b


def interceptor(fn):
    def intercept(*args, **kwargs):
        global args_captured, kwargs_captured
        args_captured = args
        kwargs_captured = kwargs
        fn(*args, **kwargs)

    return intercept


def test_interceptor():
    target = Target()
    for name, fn in inspect.getmembers(target):
        if inspect.ismethod(fn):
            setattr(target, name, interceptor(fn))
    target.do_stuff(1, b=20)
    assert args_captured == (1,)
    assert kwargs_captured == {"b": 20}
    assert a_captured == 1
    assert b_captured == 20

    target2 = Target()
    target2.do_stuff(99, b=100)
    assert args_captured == (1,)
    assert kwargs_captured == {"b": 20}


def test_logger():
    reset_counter_filter_counter()

    logging.config.dictConfig(LOGGING)
    logger = logging.getLogger("test-logger")
    logger.info("1")
    logger.info("2")
    logger.info("3")

    logger = logging.getLogger("something-else")
    logger.info("1")
    logger.info("2")
    logger.info("3")

    assert get_counter_filter_counter() == 3
