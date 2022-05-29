import os
import re
import shlex
from subprocess import PIPE, Popen
from typing import Any, Final, List, Optional, Union

import attr
from reactivex import Observable, abc, create
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable
from reactivex.scheduler.currentthreadscheduler import CurrentThreadScheduler
from tqdm import tqdm

__all__ = 'RemuxingResult', 'remux_video'


@attr.s(auto_attribs=True, slots=True, frozen=True)
class RemuxingProgress:
    count: int
    total: int


@attr.s(auto_attribs=True, slots=True, frozen=True)
class RemuxingResult:
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


def remux_video(
    in_path: str,
    out_path: str,
    metadata_path: Optional[str] = None,
    *,
    show_progress: bool = False,
    remove_filler_data: bool = False,
) -> Observable[Union[RemuxingProgress, RemuxingResult]]:
    SIZE_PATTERN: Final = re.compile(r'size=\s*(?P<number>\d+)(?P<unit>[a-zA-Z]?B)')
    filesize = os.path.getsize(in_path)
    filename = os.path.basename(in_path)

    def parse_size(line: str) -> int:
        match = SIZE_PATTERN.search(line)
        assert match is not None
        result = match.groupdict()

        unit = result['unit']
        number = int(result['number'])

        if unit == 'B':
            size = number
        elif unit == 'kB':
            size = 1024 * number
        elif unit == 'MB':
            size = 1024**2 * number
        elif unit == 'GB':
            size = 1024**3 * number
        else:
            raise ValueError(unit)

        return size

    def should_output_line(line: str) -> bool:
        line = line.strip()
        return not (line.startswith('frame=') or line.startswith('Press [q]'))

    def subscribe(
        observer: abc.ObserverBase[Union[RemuxingProgress, RemuxingResult]],
        scheduler: Optional[abc.SchedulerBase] = None,
    ) -> abc.DisposableBase:
        _scheduler = scheduler or CurrentThreadScheduler.singleton()

        disposed = False
        cancelable = SerialDisposable()

        def action(scheduler: abc.SchedulerBase, state: Optional[Any] = None) -> None:
            if disposed:
                return

            with tqdm(
                desc='Remuxing',
                total=filesize,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                postfix=filename,
                disable=not show_progress,
            ) as pbar:
                cmd = f'ffmpeg -i "{in_path}"'
                if metadata_path is not None:
                    cmd += f' -i "{metadata_path}" -map_metadata 1'
                cmd += ' -codec copy'
                if remove_filler_data:
                    # https://forum.doom9.org/showthread.php?t=152051
                    # ISO_IEC_14496-10_2020(E)
                    # Table 7-1 – NAL unit type codes, syntax element categories, and NAL unit type classes  # noqa
                    # 7.4.2.7 Filler data RBSP semantics
                    cmd += ' -bsf:v filter_units=remove_types=12'
                cmd += f' "{out_path}" -y'

                args = shlex.split(cmd)
                out_lines: List[str] = []

                try:
                    with Popen(
                        args, stderr=PIPE, encoding='utf8', errors='backslashreplace'
                    ) as process:
                        assert process.stderr is not None
                        while not disposed:
                            line = process.stderr.readline()
                            if not line:
                                if process.poll() is not None:
                                    break
                                else:
                                    continue

                            if line.startswith('frame='):
                                size = parse_size(line)
                                pbar.update(size - pbar.n)
                                progress = RemuxingProgress(size, filesize)
                                observer.on_next(progress)

                            if should_output_line(line):
                                out_lines.append(line)

                        if not disposed and process.returncode == 0:
                            pbar.update(filesize)
                            progress = RemuxingProgress(filesize, filesize)
                            observer.on_next(progress)
                except Exception as e:
                    observer.on_error(e)
                else:
                    result = RemuxingResult(process.returncode, ''.join(out_lines))
                    observer.on_next(result)
                    observer.on_completed()

        cancelable.disposable = _scheduler.schedule(action)

        def dispose() -> None:
            nonlocal disposed
            disposed = True

        return CompositeDisposable(cancelable, Disposable(dispose))

    return create(subscribe)
