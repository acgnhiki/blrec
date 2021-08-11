from typing import Optional

import aiohttp


from .api import PypiApi
from .typing import Metadata


__all__ = (
    'get_project_metadata',
    'get_release_metadata',
    'get_latest_version_string',
)


async def get_project_metadata(project_name: str) -> Optional[Metadata]:
    async with aiohttp.ClientSession(raise_for_status=True) as session:
        api = PypiApi(session)
        return await api.get_project_metadata(project_name)


async def get_release_metadata(
    project_name: str, version: str
) -> Optional[Metadata]:
    async with aiohttp.ClientSession(raise_for_status=True) as session:
        api = PypiApi(session)
        return await api.get_release_metadata(project_name, version)


async def get_latest_version_string(project_name: str) -> Optional[str]:
    metadata = await get_project_metadata(project_name)
    if not metadata:
        return None
    return metadata['info']['version']
