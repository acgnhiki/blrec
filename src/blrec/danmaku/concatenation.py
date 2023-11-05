from typing import Iterable

from .common import copy_damus
from .io import DanmakuReader, DanmakuWriter

__all__ = 'DanmakuConcatenator'


class DanmakuConcatenator:
    def __init__(
        self, in_paths: Iterable[str], deltas: Iterable[int], out_path: str
    ) -> None:
        self._in_paths = list(in_paths)
        self._deltas = list(deltas)
        self._out_path = out_path
        assert len(self._in_paths) == len(self._deltas)

    async def concat(self) -> None:
        async with DanmakuWriter(self._out_path) as writer:
            async with DanmakuReader(self._in_paths[0]) as reader:
                metadata = await reader.read_metadata()
                await writer.write_metadata(metadata)
                await copy_damus(reader, writer, delta=self._deltas[0])

            for path, delta in zip(self._in_paths[1:], self._deltas[1:]):
                async with DanmakuReader(path) as reader:
                    await copy_damus(reader, writer, delta=delta)
