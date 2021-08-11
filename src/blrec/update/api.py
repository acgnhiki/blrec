from http import HTTPStatus
from typing import Any, Final, Optional

import aiohttp
from tenacity import (
    retry,
    wait_exponential,
    stop_after_delay,
)

from .typing import JsonResponse, Metadata


__all__ = 'PypiApi',


class PypiApi:
    BASE_URL: Final[str] = 'https://pypi.org/pypi'

    def __init__(self, session: aiohttp.ClientSession):
        self._session = session

    @classmethod
    def _make_url(cls, path: str) -> str:
        return cls.BASE_URL + path

    @retry(
        reraise=True,
        stop=stop_after_delay(5),
        wait=wait_exponential(0.1),
    )
    async def _get(self, *args: Any, **kwds: Any) -> Optional[JsonResponse]:
        try:
            async with self._session.get(
                *args, raise_for_status=True, timeout=10, **kwds
            ) as res:
                return await res.json()
        except aiohttp.ClientResponseError as e:
            if e.status == HTTPStatus.NOT_FOUND:
                return None
            else:
                raise

    async def get_project_metadata(
        self, project_name: str
    ) -> Optional[Metadata]:
        url = self._make_url(f'/{project_name}/json')
        return await self._get(url)

    async def get_release_metadata(
        self, project_name: str, version: str
    ) -> Optional[Metadata]:
        url = self._make_url(f'/{project_name}/{version}/json')
        return await self._get(url)
