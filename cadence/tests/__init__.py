import logging

def init_test_logging():
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            'cadence': {
                'handlers': ['console'],
                'level': 'DEBUG',
            },
        },
    })
