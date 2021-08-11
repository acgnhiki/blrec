import logging
from typing import Iterable


from .io import DanmakuReader, DanmakuWriter
from .common import copy_damus
from .typing import TimebaseType


__all__ = 'TimebaseType', 'DanmakuCombinator'


logger = logging.getLogger(__name__)


class DanmakuCombinator:
    def __init__(
        self,
        in_paths: Iterable[str],
        out_path: str,
        timebase_type: TimebaseType = TimebaseType.RECORD,
    ) -> None:
        self._in_paths = list(in_paths)
        self._out_path = out_path
        self._timebase_type = timebase_type

    async def combine(self) -> None:
        async with DanmakuWriter(self._out_path) as writer:
            writer = writer

            async with DanmakuReader(self._in_paths[0]) as reader:
                metadata = await reader.read_metadata()
                await writer.write_metadata(metadata)

                if self._timebase_type == TimebaseType.LIVE:
                    timebase = metadata.live_start_time * 1000
                else:
                    timebase = metadata.record_start_time * 1000

                await copy_damus(reader, writer, timebase=timebase)

            for path in self._in_paths[1:]:
                async with DanmakuReader(path) as reader:
                    await copy_damus(reader, writer, timebase=timebase)
