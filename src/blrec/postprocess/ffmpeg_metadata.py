import json
from typing import Iterable, cast

import aiofiles

from .helpers import get_metadata, get_extra_metadata
from ..flv.stream_processor import JoinPoint
from ..flv.helpers import make_comment_for_joinpoints


async def make_metadata_file(flv_path: str) -> str:
    path = flv_path + '.meta'
    async with aiofiles.open(path, 'wb') as f:
        content = await _make_metadata_content(flv_path)
        await f.write(content.encode(encoding='utf8'))
    return path


async def _make_metadata_content(flv_path: str) -> str:
    metadata = await get_metadata(flv_path)
    extra_metadata = await get_extra_metadata(flv_path)

    comment = cast(str, metadata.get('Comment', ''))
    chapters = ''

    if (join_points := extra_metadata.get('joinpoints')):
        join_points = list(map(JoinPoint.from_metadata_value, join_points))
        comment += '\n\n' + make_comment_for_joinpoints(join_points)
        duration = int(cast(float, metadata['duration']) * 1000)
        chapters = _make_chapters(join_points, duration)

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


def _make_chapters(
    join_points: Iterable[JoinPoint], duration: int
) -> str:
    join_points = filter(lambda p: not p.seamless, join_points)
    timestamps = list(map(lambda p: p.timestamp, join_points))
    if not timestamps:
        return ''
    timestamps.insert(0, 0)
    timestamps.append(duration)

    result = ''
    for i in range(1, len(timestamps)):
        result += f"""\
[CHAPTER]
TIMEBASE=1/1000
START={timestamps[i-1]}
END={timestamps[i]}
title=segment \\#{i}
"""
    return result
