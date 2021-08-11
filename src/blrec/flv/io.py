from io import SEEK_CUR
import logging
from typing import Iterable, Iterator


from .format import FlvParser, FlvDumper
from .models import FlvHeader, FlvTag, BACK_POINTER_SIZE
from .utils import OffsetRepositor, AutoRollbacker
from .io_protocols import RandomIO


__all__ = 'FlvReader', 'FlvWriter'


logger = logging.getLogger(__name__)


class FlvReader:
    def __init__(self, stream: RandomIO) -> None:
        self._stream = stream
        self._parser = FlvParser(stream)

    def read_header(self) -> FlvHeader:
        header = self._parser.parse_header()
        previous_tag_size = self._parser.parse_previous_tag_size()
        assert previous_tag_size == 0
        return header

    def read_tag(self, *, no_body: bool = False) -> FlvTag:
        tag = self._parser.parse_tag(no_body=no_body)
        previous_tag_size = self._parser.parse_previous_tag_size()
        assert previous_tag_size == tag.tag_size
        return tag

    def read_tags(self, *, no_body: bool = False) -> Iterator[FlvTag]:
        while True:
            try:
                yield self.read_tag(no_body=no_body)
            except EOFError:
                break

    def rread_tag(self, *, no_body: bool = False) -> FlvTag:
        self._seek_to_previous_tag()
        with OffsetRepositor(self._stream):
            return self.read_tag(no_body=no_body)

    def rread_tags(
        self, *, no_body: bool = False
    ) -> Iterator[FlvTag]:
        while True:
            try:
                yield self.rread_tag(no_body=no_body)
            except EOFError:
                break

    def read_body(self, tag: FlvTag) -> bytes:
        with OffsetRepositor(self._stream):
            self._stream.seek(tag.body_offset)
            return self._stream.read(tag.body_size)

    def _seek_to_previous_tag(self) -> int:
        self._stream.seek(-BACK_POINTER_SIZE, SEEK_CUR)
        previous_tag_size = self._parser.parse_previous_tag_size()
        return self._stream.seek(-(4 + previous_tag_size), SEEK_CUR)


class FlvWriter:
    def __init__(self, stream: RandomIO) -> None:
        self._stream = stream
        self._dumper = FlvDumper(stream)

    def write_header(self, header: FlvHeader) -> int:
        with AutoRollbacker(self._stream):
            self._dumper.dump_header(header)
            self._dumper.dump_previous_tag_size(0)
            return header.size + BACK_POINTER_SIZE

    def write_tag(self, tag: FlvTag) -> int:
        with AutoRollbacker(self._stream):
            self._dumper.dump_tag(tag)
            self._dumper.dump_previous_tag_size(tag.tag_size)
            return tag.tag_size + BACK_POINTER_SIZE

    def write_tags(self, tags: Iterable[FlvTag]) -> int:
        return sum(map(self.write_tag, tags))
