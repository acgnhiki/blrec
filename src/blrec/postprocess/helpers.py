import asyncio
from typing import Any, Dict, Iterable, Literal

from ..flv.helpers import get_metadata as _get_metadata
from ..flv.helpers import get_extra_metadata as _get_extra_metadata


async def discard_files(
    paths: Iterable[str],
    log_level: Literal['INFO', 'DEBUG'] = 'INFO',
) -> None:
    for path in paths:
        await discard_file(path, log_level)


async def discard_file(
    path: str,
    log_level: Literal['INFO', 'DEBUG'] = 'INFO',
) -> None:
    from ..disk_space import delete_file
    await delete_file(path, log_level)


async def get_metadata(flv_path: str) -> Dict[str, Any]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _get_metadata, flv_path)


async def get_extra_metadata(flv_path: str) -> Dict[str, Any]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _get_extra_metadata, flv_path)
