import io

from reactivex import of

from .parse import parse
from .typing import FLVStream

__all__ = ('from_file', 'from_stream')


def from_stream(
    stream: io.RawIOBase,
    *,
    complete_on_eof: bool = False,
    backup_timestamp: bool = False,
    restore_timestamp: bool = False,
) -> FLVStream:
    return of(stream).pipe(
        parse(
            complete_on_eof=complete_on_eof,
            backup_timestamp=backup_timestamp,
            restore_timestamp=restore_timestamp,
        )
    )


def from_file(
    path: str, *, backup_timestamp: bool = False, restore_timestamp: bool = False
) -> FLVStream:
    return from_stream(
        open(path, 'rb'),  # type: ignore
        complete_on_eof=True,
        backup_timestamp=backup_timestamp,
        restore_timestamp=restore_timestamp,
    )
