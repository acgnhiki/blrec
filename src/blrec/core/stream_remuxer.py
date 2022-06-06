import errno
import io
import logging
from contextlib import suppress
import os
import re
import shlex
from subprocess import PIPE, CalledProcessError, Popen
from threading import Condition, Thread
from typing import Optional, cast

from ..utils.io import wait_for
from ..utils.mixins import StoppableMixin, SupportDebugMixin

logger = logging.getLogger(__name__)


__all__ = ('StreamRemuxer',)


class FFmpegError(Exception):
    pass


class StreamRemuxer(StoppableMixin, SupportDebugMixin):
    _ERROR_PATTERN = re.compile(
        r'\b(error|failed|missing|invalid|corrupt)\b', re.IGNORECASE
    )

    def __init__(self, room_id: int, remove_filler_data: bool = False) -> None:
        super().__init__()
        self._room_id = room_id
        self._remove_filler_data = remove_filler_data
        self._exception: Optional[Exception] = None
        self._ready = Condition()
        self._env = None

        self._init_for_debug(room_id)
        if self._debug:
            self._env = os.environ.copy()
            path = os.path.join(self._debug_dir, f'ffreport-{room_id}-%t.log')
            self._env['FFREPORT'] = f'file={path}:level=48'

    @property
    def input(self) -> io.BufferedWriter:
        assert self._subprocess.stdin is not None
        return cast(io.BufferedWriter, self._subprocess.stdin)

    @property
    def output(self) -> io.BufferedReader:
        assert self._subprocess.stdout is not None
        return cast(io.BufferedReader, self._subprocess.stdout)

    @property
    def exception(self) -> Optional[Exception]:
        return self._exception

    def __enter__(self):  # type: ignore
        self.start()
        self.wait()
        return self

    def __exit__(self, exc_type, value, traceback):  # type: ignore
        self.stop()
        self.raise_for_exception()

    def wait(self, timeout: Optional[float] = None) -> bool:
        with self._ready:
            return self._ready.wait(timeout=timeout)

    def restart(self) -> None:
        logger.debug('Restarting stream remuxer...')
        self.stop()
        self.start()
        logger.debug('Restarted stream remuxer')

    def raise_for_exception(self) -> None:
        if not self.exception:
            return
        raise self.exception

    def _do_start(self) -> None:
        logger.debug('Starting stream remuxer...')
        self._thread = Thread(
            target=self._run, name=f'StreamRemuxer::{self._room_id}', daemon=True
        )
        self._thread.start()

    def _do_stop(self) -> None:
        logger.debug('Stopping stream remuxer...')
        if hasattr(self, '_subprocess'):
            with suppress(ProcessLookupError):
                self._subprocess.kill()
            self._subprocess.wait(timeout=10)
        if hasattr(self, '_thread'):
            self._thread.join(timeout=10)

    def _run(self) -> None:
        logger.debug('Started stream remuxer')
        self._exception = None
        try:
            self._run_subprocess()
        except BrokenPipeError as exc:
            logger.debug(repr(exc))
        except FFmpegError as exc:
            if not self._stopped:
                logger.warning(repr(exc))
            else:
                logger.debug(repr(exc))
        except TimeoutError as exc:
            logger.debug(repr(exc))
        except Exception as exc:
            # OSError: [Errno 22] Invalid argument
            # https://stackoverflow.com/questions/23688492/oserror-errno-22-invalid-argument-in-subprocess
            if isinstance(exc, OSError) and exc.errno == errno.EINVAL:
                pass
            else:
                self._exception = exc
                logger.exception(exc)
        finally:
            self._stopped = True
            logger.debug('Stopped stream remuxer')

    def _run_subprocess(self) -> None:
        cmd = 'ffmpeg -xerror -i pipe:0 -c copy -copyts'
        if self._remove_filler_data:
            cmd += ' -bsf:v filter_units=remove_types=12'
        cmd += ' -f flv pipe:1'
        args = shlex.split(cmd)

        with Popen(
            args, stdin=PIPE, stdout=PIPE, stderr=PIPE, env=self._env
        ) as self._subprocess:
            with self._ready:
                self._ready.notify_all()

            assert self._subprocess.stderr is not None
            with io.TextIOWrapper(
                self._subprocess.stderr, encoding='utf-8', errors='backslashreplace'
            ) as stderr:
                while not self._stopped:
                    line = wait_for(stderr.readline, timeout=10)
                    if not line:
                        if self._subprocess.poll() is not None:
                            break
                        else:
                            continue
                    if self._debug:
                        logger.debug('ffmpeg: %s', line)
                    self._check_error(line)

        if not self._stopped and self._subprocess.returncode not in (0, 255):
            # 255: Exiting normally, received signal 2.
            raise CalledProcessError(self._subprocess.returncode, cmd=cmd)

    def _check_error(self, line: str) -> None:
        match = self._ERROR_PATTERN.search(line)
        if not match:
            return
        raise FFmpegError(line)
