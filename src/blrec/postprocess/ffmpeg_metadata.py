from __future__ import annotations

import asyncio
import json
import os
from decimal import Decimal
from typing import Iterable, List, Tuple, cast

import aiofiles
import m3u8
from loguru import logger

from blrec.flv.helpers import make_comment_for_joinpoints
from blrec.flv.operators import JoinPoint
from blrec.flv.utils import format_timestamp
from blrec.path.helpers import ffmpeg_metadata_path, playlist_path

from .helpers import get_extra_metadata, get_metadata, get_record_metadata


async def make_metadata_file(video_path: str) -> str:
    path = ffmpeg_metadata_path(video_path)

    async with aiofiles.open(path, 'wb') as file:
        _, ext = os.path.splitext(video_path)
        if ext == '.flv':
            content = await _make_metadata_content_for_flv(video_path)
        elif ext == '.m4s':
            content = await _make_metadata_content_for_m3u8(playlist_path(video_path))
        else:
            raise NotImplementedError(video_path)
        await file.write(content.encode(encoding='utf8'))
    return path


async def _make_metadata_content_for_flv(flv_path: str) -> str:
    metadata = await get_metadata(flv_path)
    try:
        extra_metadata = await get_extra_metadata(flv_path)
    except Exception as e:
        logger.warning(f'Failed to get extra metadata: {repr(e)}')
        extra_metadata = {}

    comment = cast(str, metadata.get('Comment', ''))
    chapters = ''

    if join_points := extra_metadata.get('joinpoints'):
        join_points = list(map(JoinPoint.from_metadata_value, join_points))
        comment += '\n\n' + make_comment_for_joinpoints(join_points)
        last_timestamp = int(
            cast(float, extra_metadata.get('duration') or metadata.get('duration'))
            * 1000
        )
        chapters = _make_chapters_for_flv(join_points, last_timestamp)

    comment = '\\\n'.join(comment.splitlines())

    # ref: https://ffmpeg.org/ffmpeg-formats.html#Metadata-1
    return f"""\
;FFMETADATA1
Title={metadata['Title']}
Artist={metadata['Artist']}
Date={metadata['Date']}
# Description may be truncated!
Description={json.dumps(metadata['description'], ensure_ascii=False)}
Comment={comment}

{chapters}
"""


def _make_chapters_for_flv(
    join_points: Iterable[JoinPoint], last_timestamp: int
) -> str:
    join_points = filter(lambda p: not p.seamless, join_points)
    timestamps = list(map(lambda p: p.timestamp, join_points))
    if not timestamps:
        return ''
    timestamps.insert(0, 0)
    timestamps.append(last_timestamp)

    result = ''
    for i in range(1, len(timestamps)):
        start = timestamps[i - 1]
        end = timestamps[i]
        if end < start:
            logger.warning(f'Chapter end time {end} before start {start}')
            end = start
        result += f"""\
[CHAPTER]
TIMEBASE=1/1000
START={start}
END={end}
title=segment \\#{i}
"""
    return result


async def _make_metadata_content_for_m3u8(playlist_path: str) -> str:
    metadata = await get_record_metadata(playlist_path)
    comment = cast(str, metadata.get('Comment', ''))
    chapters = ''

    timestamps, duration = await _get_discontinuities(playlist_path)
    if timestamps:
        comment += '\n\n' + _make_comment_for_discontinuities(timestamps)
        chapters = _make_chapters_for_m3u8(timestamps, duration)

    comment = '\\\n'.join(comment.splitlines())

    # ref: https://ffmpeg.org/ffmpeg-formats.html#Metadata-1
    return f"""\
;FFMETADATA1
Title={metadata['Title']}
Artist={metadata['Artist']}
Date={metadata['Date']}
# Description may be truncated!
Description={json.dumps(metadata['description'], ensure_ascii=False)}
Comment={comment}

{chapters}
"""


def _make_chapters_for_m3u8(timestamps: Iterable[int], duration: float) -> str:
    timestamps = list(timestamps)
    if not timestamps:
        return ''

    timestamps.insert(0, 0)
    timestamps.append(int(duration * 1000))

    result = ''
    for i in range(1, len(timestamps)):
        start = timestamps[i - 1]
        end = timestamps[i]
        if end < start:
            logger.warning(f'Chapter end time {end} before start {start}')
            end = start
        result += f"""\
[CHAPTER]
TIMEBASE=1/1000
START={start}
END={end}
title=segment \\#{i}
"""
    return result


def _make_comment_for_discontinuities(timestamps: Iterable[int]) -> str:
    return 'HLS片段不连续位置：\n' + '\n'.join(
        ('时间戳：{}'.format(format_timestamp(ts)) for ts in timestamps)
    )


async def _get_discontinuities(playlist_path: str) -> Tuple[List[int], float]:
    loop = asyncio.get_running_loop()
    async with aiofiles.open(playlist_path, encoding='utf8') as file:
        content = await file.read()
        playlist = await loop.run_in_executor(None, m3u8.loads, content)
        duration = Decimal()
        timestamps: List[int] = []
        for seg in playlist.segments:
            if seg.discontinuity:
                timestamps.append(int(duration * 1000))
            duration += Decimal(str(seg.duration))
        return timestamps, float(duration)
