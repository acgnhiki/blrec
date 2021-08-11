import os
import logging
from logging import LogRecord, Handler
from logging.handlers import RotatingFileHandler
from datetime import datetime
import asyncio
import threading
import atexit
from typing import Any, List, Optional

from colorama import init, deinit, Fore, Back, Style
from tqdm import tqdm

from .typing import LOG_LEVEL


__all__ = 'configure_logger', 'ConsoleHandler', 'TqdmOutputStream'


class TqdmOutputStream:
    def write(self, string: str = '') -> None:
        tqdm.write(string, end='')


class ConsoleHandler(logging.StreamHandler):
    def __init__(self, stream=None) -> None:  # type: ignore
        super().__init__(stream)

    def format(self, record: LogRecord) -> str:
        msg = super().format(record)

        level = record.levelno
        if level == logging.DEBUG:
            style = Fore.GREEN
        elif level == logging.WARNING:
            style = Fore.YELLOW
        elif level == logging.ERROR:
            style = Fore.RED
        elif level == logging.CRITICAL:
            style = Fore.WHITE + Back.RED + Style.BRIGHT
        else:
            style = ''

        return style + msg + Style.RESET_ALL if style else msg


_old_factory = logging.getLogRecordFactory()


def obtain_room_id() -> str:
    try:
        task = asyncio.current_task()
        assert task is not None
    except Exception:
        name = threading.current_thread().getName()
    else:
        name = task.get_name()

    if '::' in name:
        if (room_id := name.split('::')[-1]):
            return room_id

    return ''


def record_factory(*args: Any, **kwargs: Any) -> LogRecord:
    record = _old_factory(*args, **kwargs)

    if (room_id := obtain_room_id()):
        record.roomid = '[' + room_id + '] '  # type: ignore
    else:
        record.roomid = ''  # type: ignore

    return record


logging.setLogRecordFactory(record_factory)


_old_handlers: List[Handler] = []


def configure_logger(
    out_dir: str,
    *,
    console_log_level: LOG_LEVEL = 'INFO',
    max_bytes: Optional[int] = None,
    backup_count: Optional[int] = None,
) -> None:
    # config root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # config formatter
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(module)s] %(roomid)s%(message)s'
    )

    # logging to console
    console_handler = ConsoleHandler(TqdmOutputStream())
    console_handler.setLevel(logging.getLevelName(console_log_level))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # logging to file
    file_handler = RotatingFileHandler(
        make_log_file_path(out_dir),
        maxBytes=max_bytes or 1024 ** 2 * 10,
        backupCount=backup_count or 1,
        encoding='utf-8',
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # remove old handlers after re-configured
    for handler in _old_handlers:
        logger.removeHandler(handler)

    # retain old handlers for the removing
    _old_handlers.append(console_handler)
    _old_handlers.append(file_handler)


def make_log_file_path(out_dir: str) -> str:
    data_time_string = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    filename = f'blrec_{data_time_string}.log'
    path = os.path.join(out_dir, filename)
    return path


init()
atexit.register(deinit)
