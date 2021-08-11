

from .io_protocols import RandomIO


def format_timestamp(ts: int) -> str:
    milliseconds = ts % 1000
    seconds = ts // 1000 % 60
    minutes = ts // 1000 // 60 % 60
    hours = ts // 1000 // 60 // 60 % 60
    return f'{hours:0>2}:{minutes:0>2}:{seconds:0>2}.{milliseconds:0>3}'


def format_offest(offset: int) -> str:
    return f'0x{offset:0>8x}'


class OffsetRepositor:
    def __init__(self, file: RandomIO):
        self._file = file

    def __enter__(self):  # type: ignore
        self._offset = self._file.tell()

    def __exit__(self, exc_type, exc_val, exc_tb):  # type: ignore
        self._file.seek(self._offset)


class AutoRollbacker:
    def __init__(self, file: RandomIO):
        self._file = file

    def __enter__(self):  # type: ignore
        self._offset = self._file.tell()

    def __exit__(self, exc_type, exc_val, exc_tb):  # type: ignore
        if exc_type is not None:
            self._file.seek(self._offset)
            self._file.truncate()
