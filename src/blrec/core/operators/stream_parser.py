from __future__ import annotations

import io

from loguru import logger
from reactivex import Observable
from reactivex import operators as ops

from blrec.flv import operators as flv_ops
from blrec.flv.exceptions import FlvDataError
from blrec.flv.operators.typing import FLVStream
from blrec.utils import operators as utils_ops

from ..stream_param_holder import StreamParamHolder

__all__ = ('StreamParser',)


class StreamParser:
    def __init__(
        self,
        stream_param_holder: StreamParamHolder,
        *,
        ignore_eof: bool = False,
        ignore_value_error: bool = False,
    ) -> None:
        self._stream_param_holder = stream_param_holder
        self._ignore_eof = ignore_eof
        self._ignore_value_error = ignore_value_error

    def __call__(self, source: Observable[io.RawIOBase]) -> FLVStream:
        return source.pipe(  # type: ignore
            flv_ops.parse(
                ignore_eof=self._ignore_eof,
                ignore_value_error=self._ignore_value_error,
                backup_timestamp=True,
            ),
            ops.do_action(on_error=self._before_retry),
            utils_ops.retry(should_retry=self._should_retry),
        )

    def _should_retry(self, exc: Exception) -> bool:
        if isinstance(exc, (EOFError, FlvDataError)):
            return True
        else:
            return False

    def _before_retry(self, exc: Exception) -> None:
        try:
            raise exc
        except EOFError:
            logger.debug(repr(exc))
        except FlvDataError:
            logger.warning(f'Failed to parse stream: {repr(exc)}')
            if not self._stream_param_holder.use_alternative_stream:
                self._stream_param_holder.use_alternative_stream = True
            else:
                self._stream_param_holder.use_alternative_stream = False
                # self._stream_param_holder.rotate_api_platform()  # XXX: use web api only  # noqa
        except Exception:
            pass
