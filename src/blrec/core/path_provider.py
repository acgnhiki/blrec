import asyncio
import logging
import os
import re
import time
from datetime import datetime
from typing import Tuple

import aiohttp
from tenacity import retry, retry_if_exception_type, stop_after_delay, wait_exponential

from ..bili.live import Live
from ..path import escape_path
from ..utils.mixins import AsyncCooperationMixin

__all__ = ('PathProvider',)

logger = logging.getLogger(__name__)


class PathProvider(AsyncCooperationMixin):
    def __init__(self, live: Live, out_dir: str, path_template: str) -> None:
        super().__init__()
        self._live = live
        self.out_dir = out_dir
        self.path_template = path_template

    def __call__(self) -> Tuple[str, int]:
        timestamp = self._get_timestamp()
        path = self._make_path(timestamp)
        return path, timestamp

    def _get_timestamp(self) -> int:
        try:
            return self._get_server_timestamp()
        except Exception as e:
            logger.warning(f'Failed to get server timestamp: {repr(e)}')
            return self._get_local_timestamp()

    def _get_local_timestamp(self) -> int:
        return int(time.time())

    @retry(
        reraise=True,
        retry=retry_if_exception_type((asyncio.TimeoutError, aiohttp.ClientError)),
        wait=wait_exponential(multiplier=0.1, max=1),
        stop=stop_after_delay(3),
    )
    def _get_server_timestamp(self) -> int:
        return self._run_coroutine(self._live.get_server_timestamp())

    def _make_path(self, timestamp: int) -> str:
        date_time = datetime.fromtimestamp(timestamp)
        relpath = self.path_template.format(
            roomid=self._live.room_id,
            uname=escape_path(self._live.user_info.name),
            title=escape_path(self._live.room_info.title),
            area=escape_path(self._live.room_info.area_name),
            parent_area=escape_path(self._live.room_info.parent_area_name),
            year=date_time.year,
            month=str(date_time.month).rjust(2, '0'),
            day=str(date_time.day).rjust(2, '0'),
            hour=str(date_time.hour).rjust(2, '0'),
            minute=str(date_time.minute).rjust(2, '0'),
            second=str(date_time.second).rjust(2, '0'),
        )

        pathname = os.path.abspath(
            os.path.expanduser(os.path.join(self.out_dir, relpath) + '.flv')
        )
        os.makedirs(os.path.dirname(pathname), exist_ok=True)
        while os.path.exists(pathname):
            root, ext = os.path.splitext(pathname)
            m = re.search(r'_\((\d+)\)$', root)
            if m is None:
                root += '_(1)'
            else:
                root = re.sub(r'\(\d+\)$', f'({int(m.group(1)) + 1})', root)
            pathname = root + ext

        return pathname
