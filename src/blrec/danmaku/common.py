
from typing import Optional

import attr

from .io import DanmakuReader, DanmakuWriter


async def copy_damus(
    reader: DanmakuReader,
    writer: DanmakuWriter,
    *,
    timebase: Optional[int] = None,  # milliseconds
    delta: int = 0,  # milliseconds
) -> None:
    async for danmu in reader.read_danmus():
        if timebase is None:
            stime = max(0, danmu.stime * 1000 + delta) / 1000
        else:
            stime = max(0, danmu.date - timebase + delta) / 1000
        new_danmu = attr.evolve(danmu, stime=stime)
        await writer.write_danmu(new_danmu)
