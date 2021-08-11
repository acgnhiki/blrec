import os
import re
import shlex
from subprocess import Popen, PIPE
from typing import Final, List, Match, Optional, Union

import attr
from rx import create, operators as op
from rx.subject import Subject
from rx.core import Observable
from rx.core.typing import Observer, Scheduler, Disposable
from rx.scheduler.currentthreadscheduler import CurrentThreadScheduler
from tqdm import tqdm


__all__ = 'VideoRemuxer', 'RemuxResult', 'remux_video'


@attr.s(auto_attribs=True, slots=True, frozen=True)
class RemuxProgress:
    time: int
    duration: int


@attr.s(auto_attribs=True, slots=True, frozen=True)
class RemuxResult:
    return_code: int
    output: str

    def is_done(self) -> bool:
        return self.return_code == 0

    def is_successful(self) -> bool:
        return self.is_done() and not self.may_timestamps_incorrect()

    def is_warned(self) -> bool:
        return self.is_done() and self.may_timestamps_incorrect()

    def is_failed(self) -> bool:
        return not self.is_done()

    def may_timestamps_incorrect(self) -> bool:
        return 'Non-monotonous DTS in output stream' in self.output


class VideoRemuxer:
    _TIME_PATTERN: Final = re.compile(
        r'(?P<hour>\d+):(?P<minute>\d+):(?P<second>\d+).(?P<millisecond>\d+)'
    )

    def __init__(self) -> None:
        self._duration: int = 0
        self._progress_updates = Subject()

    @property
    def progress_updates(self) -> Observable:
        return self._progress_updates

    def remux(
        self,
        in_path: str,
        out_path: str,
        metadata_path: Optional[str] = None,
    ) -> RemuxResult:
        if metadata_path is not None:
            cmd = f'ffmpeg -i "{in_path}" -i "{metadata_path}" ' \
                f'-map_metadata 1 -codec copy "{out_path}" -y'
        else:
            cmd = f'ffmpeg -i "{in_path}" -codec copy "{out_path}" -y'

        args = shlex.split(cmd)
        out_lines: List[str] = []

        with Popen(
            args, stderr=PIPE, encoding='utf8', errors='backslashreplace'
        ) as process:
            assert process.stderr is not None
            while True:
                line = process.stderr.readline()
                if not line:
                    if process.poll() is not None:
                        break
                    else:
                        continue
                self._parse_line(line)
                if self._should_output_line(line):
                    out_lines.append(line)

        if process.returncode == 0:
            self._complete_progress_updates()

        return RemuxResult(process.returncode, ''.join(out_lines))

    def _parse_line(self, line: str) -> None:
        line = line.strip()
        if line.startswith('frame='):
            self._parse_time(line)
        elif line.startswith('Duration:'):
            self._parse_duration(line)
        else:
            pass

    def _parse_duration(self, line: str) -> None:
        match = self._TIME_PATTERN.search(line)
        if match is not None:
            self._duration = self._calc_time(match)
            self._progress_updates.on_next(RemuxProgress(0, self._duration))

    def _parse_time(self, line: str) -> None:
        match = self._TIME_PATTERN.search(line)
        if match is not None:
            progress = RemuxProgress(self._calc_time(match), self._duration)
            self._progress_updates.on_next(progress)

    def _complete_progress_updates(self) -> None:
        progress = RemuxProgress(self._duration, self._duration)
        self._progress_updates.on_next(progress)
        self._progress_updates.on_completed()

    def _calc_time(self, match: Match[str]) -> int:
        result = match.groupdict()
        return (
            int(result['hour']) * 60 * 60 * 1000 +
            int(result['minute']) * 60 * 1000 +
            int(result['second']) * 1000 +
            int(result['millisecond'])
        )

    def _should_output_line(self, line: str) -> bool:
        line = line.strip()
        return not (
            line.startswith('frame=') or
            line.startswith('Press [q]')
        )


def remux_video(
    in_path: str,
    out_path: str,
    metadata_path: Optional[str] = None,
    *,
    report_progress: bool = False,
) -> Observable:
    def subscribe(
        observer: Observer[Union[RemuxProgress, RemuxResult]],
        scheduler: Optional[Scheduler] = None,
    ) -> Disposable:
        _scheduler = scheduler or CurrentThreadScheduler.singleton()

        def action(scheduler, state):  # type: ignore
            remuxer = VideoRemuxer()
            file_name = os.path.basename(in_path)

            with tqdm(desc='Remuxing', unit='ms', postfix=file_name) as pbar:
                def reset(progress: RemuxProgress) -> None:
                    pbar.reset(progress.duration)

                def update(progress: RemuxProgress) -> None:
                    pbar.update(progress.time - pbar.n)

                remuxer.progress_updates.pipe(op.first()).subscribe(reset)
                remuxer.progress_updates.pipe(op.skip(1)).subscribe(update)

                if report_progress:
                    remuxer.progress_updates.subscribe(
                        lambda p: observer.on_next(p)
                    )

                try:
                    result = remuxer.remux(in_path, out_path, metadata_path)
                except Exception as e:
                    observer.on_error(e)
                else:
                    observer.on_next(result)
                    observer.on_completed()

        return _scheduler.schedule(action)

    return create(subscribe)
