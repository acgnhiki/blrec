import os
import io
import errno
import shlex
import logging
from threading import Thread, Event
from subprocess import Popen, PIPE, CalledProcessError
from typing import List, Optional, cast


from ..utils.mixins import StoppableMixin, SupportDebugMixin


logger = logging.getLogger(__name__)


__all__ = 'StreamRemuxer',


class StreamRemuxer(StoppableMixin, SupportDebugMixin):
    def __init__(self, room_id: int, bufsize: int = 1024 * 1024) -> None:
        super().__init__()
        self._room_id = room_id
        self._bufsize = bufsize
        self._exception: Optional[Exception] = None
        self._subprocess_setup = Event()
        self._MAX_ERROR_MESSAGES = 10
        self._error_messages: List[str] = []
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
        self.wait_for_subprocess()
        return self

    def __exit__(self, exc_type, value, traceback):  # type: ignore
        self.stop()
        self.raise_for_exception()

    def wait_for_subprocess(self) -> None:
        self._subprocess_setup.wait()

    def raise_for_exception(self) -> None:
        if not self.exception:
            return
        raise self.exception

    def _do_start(self) -> None:
        logger.debug('Starting stream remuxer...')
        self._thread = Thread(
            target=self._run,
            name=f'StreamRemuxer::{self._room_id}',
            daemon=True,
        )
        self._thread.start()

    def _do_stop(self) -> None:
        logger.debug('Stopping stream remuxer...')
        if hasattr(self, '_subprocess'):
            self._subprocess.kill()
            self._subprocess.wait(timeout=10)
        if hasattr(self, '_thread'):
            self._thread.join(timeout=10)

    def _run(self) -> None:
        logger.debug('Started stream remuxer')
        self._exception = None
        self._error_messages.clear()
        self._subprocess_setup.clear()
        try:
            self._run_subprocess()
        except BrokenPipeError:
            pass
        except Exception as e:
            # OSError: [Errno 22] Invalid argument
            # https://stackoverflow.com/questions/23688492/oserror-errno-22-invalid-argument-in-subprocess
            if isinstance(e, OSError) and e.errno == errno.EINVAL:
                pass
            else:
                self._exception = e
                logger.exception(e)
        finally:
            logger.debug('Stopped stream remuxer')

    def _run_subprocess(self) -> None:
        cmd = 'ffmpeg -i pipe:0 -c copy -f flv pipe:1'
        args = shlex.split(cmd)

        with Popen(
            args, stdin=PIPE, stdout=PIPE, stderr=PIPE,
            bufsize=self._bufsize, env=self._env,
        ) as self._subprocess:
            self._subprocess_setup.set()
            assert self._subprocess.stderr is not None

            while not self._stopped:
                data = self._subprocess.stderr.readline()
                if not data:
                    if self._subprocess.poll() is not None:
                        break
                    else:
                        continue
                line = data.decode('utf-8', errors='backslashreplace')
                if self._debug:
                    logger.debug('ffmpeg: %s', line)
                self._check_error(line)

        if not self._stopped and self._subprocess.returncode not in (0, 255):
            # 255: Exiting normally, received signal 2.
            raise CalledProcessError(
                self._subprocess.returncode,
                cmd=cmd,
                output='\n'.join(self._error_messages),
            )

    def _check_error(self, line: str) -> None:
        if 'error' not in line.lower() and 'failed' not in line.lower():
            return
        logger.warning(f'ffmpeg error: {line}')
        self._error_messages.append(line)
        if len(self._error_messages) > self._MAX_ERROR_MESSAGES:
            self._error_messages.remove(self._error_messages[0])
