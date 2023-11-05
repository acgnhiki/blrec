import asyncio
import json
import os
import shutil
from typing import Any, Dict, Iterable, Literal

import aiofiles
from loguru import logger

from blrec.path.helpers import (
    cover_path,
    danmaku_path,
    playlist_path,
    raw_danmaku_path,
    record_metadata_path,
)

from ..flv.helpers import get_extra_metadata as _get_extra_metadata
from ..flv.helpers import get_metadata as _get_metadata


async def discard_files(
    paths: Iterable[str], log_level: Literal['INFO', 'DEBUG'] = 'INFO'
) -> None:
    for path in paths:
        await discard_file(path, log_level)


async def discard_file(path: str, log_level: Literal['INFO', 'DEBUG'] = 'INFO') -> None:
    from ..disk_space import delete_file

    await delete_file(path, log_level)


async def discard_dir(path: str, log_level: Literal['INFO', 'DEBUG'] = 'INFO') -> None:
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, shutil.rmtree, path)
    except Exception as e:
        logger.error(f'Failed to delete {path!r}, due to: {repr(e)}')
    else:
        logger.log(log_level, f'Deleted {path!r}')


def files_related(video_path: str) -> Iterable[str]:
    file_paths = [
        danmaku_path(video_path),
        raw_danmaku_path(video_path),
        cover_path(video_path, ext='jpg'),
        cover_path(video_path, ext='png'),
    ]

    if video_path.endswith('.m4s'):
        file_paths.append(playlist_path(video_path))

    for path in file_paths:
        if os.path.isfile(path):
            yield path


async def get_metadata(flv_path: str) -> Dict[str, Any]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _get_metadata, flv_path)


async def get_record_metadata(video_path: str) -> Dict[str, Any]:
    if video_path.endswith('.m3u8'):
        path = record_metadata_path(video_path)
    else:
        raise NotImplementedError(video_path)
    async with aiofiles.open(path, 'rb') as file:
        data = await file.read()
        return json.loads(data)


async def get_extra_metadata(flv_path: str) -> Dict[str, Any]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _get_extra_metadata, flv_path)
