import logging
import logging.config

counter_filter_counter = 0


class CounterFilter(logging.Filter):

    def filter(self, record):
        global counter_filter_counter
        counter_filter_counter += 1
        return True


def reset_counter_filter_counter():
    global counter_filter_counter
    counter_filter_counter = 0


def get_counter_filter_counter():
    return counter_filter_counter


LOGGING = {
    'version': 1,
    'filters': {
        'counter-filter': {
            '()': CounterFilter,
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'filters': ['counter-filter']
        }
    },
    'loggers': {
        'test-logger': {
            'level': 'DEBUG',
            'handlers': ['console']
        }
    },
}
