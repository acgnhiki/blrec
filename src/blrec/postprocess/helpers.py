import asyncio
import json
import logging
import os
import shutil
from pathlib import PurePath
from typing import Any, Dict, Iterable, Literal

import aiofiles

from blrec.path.helpers import (
    cover_path,
    danmaku_path,
    raw_danmaku_path,
    record_metadata_path,
)

from ..flv.helpers import get_extra_metadata as _get_extra_metadata
from ..flv.helpers import get_metadata as _get_metadata

logger = logging.getLogger(__name__)


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
        logger.log(logging.getLevelName(log_level), f'Deleted {path!r}')


async def copy_files_related(video_path: str) -> None:
    loop = asyncio.get_running_loop()
    dirname = os.path.dirname(video_path)

    for src_path in [
        danmaku_path(video_path),
        raw_danmaku_path(video_path),
        cover_path(video_path, ext='jpg'),
        cover_path(video_path, ext='png'),
    ]:
        if not os.path.isfile(src_path):
            continue
        root, ext = os.path.splitext(src_path)
        dst_path = PurePath(dirname).with_suffix(ext)
        try:
            await loop.run_in_executor(None, shutil.copy, src_path, dst_path)
        except Exception as e:
            logger.error(f"Failed to copy '{src_path}' to '{dst_path}': {repr(e)}")
        else:
            logger.info(f"Copied '{src_path}' to '{dst_path}'")


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
