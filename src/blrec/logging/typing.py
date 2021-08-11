from typing import Literal

# CRITICAL = 50
# FATAL = CRITICAL
# ERROR = 40
# WARNING = 30
# WARN = WARNING
# INFO = 20
# DEBUG = 10
# NOTSET = 0

LOG_LEVEL = Literal[
    'CRITICAL',
    'FATAL',
    'ERROR',
    'WARNING',
    'INFO',
    'DEBUG',
    'NOTSET',  # equivalent to verbose
]
