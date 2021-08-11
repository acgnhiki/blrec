import os
from typing import Iterable


from .io import DanmakuReader, DanmakuWriter
from .combination import DanmakuCombinator, TimebaseType
from .concatenation import DanmakuConcatenator


async def has_danmu(path: str) -> bool:
    async with DanmakuReader(path) as reader:
        async for _ in reader.read_danmus():
            return True
        return False


async def clear_danmu(path: str) -> None:
    async with DanmakuReader(path) as reader:
        async with DanmakuWriter(path) as writer:
            metadata = await reader.read_metadata()
            await writer.write_metadata(metadata)


async def concat_danmaku(
    in_paths: Iterable[str], deltas: Iterable[int], out_path: str
) -> None:
    concatenator = DanmakuConcatenator(in_paths, deltas, out_path)
    await concatenator.concat()


async def combine_danmaku(
    in_paths: Iterable[str],
    out_path: str,
    timebase_type: TimebaseType = TimebaseType.RECORD,
) -> None:
    combiator = DanmakuCombinator(in_paths, out_path, timebase_type)
    await combiator.combine()


async def merge_danmaku(src: str, dst: str, insert: bool = False) -> None:
    """Merge all danmus in the src into the dst.

    insert: if true, src insert before dst otherwise src append after dst
    """
    out = dst + '.tmp'
    if insert:
        await combine_danmaku([src, dst], out)
    else:
        await combine_danmaku([dst, src], out)
    await clear_danmu(src)
    os.replace(out, dst)
