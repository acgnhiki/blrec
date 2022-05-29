from __future__ import annotations

import json
from subprocess import PIPE, Popen
from typing import Any, Dict, Optional

from reactivex import Observable, abc
from reactivex.scheduler import NewThreadScheduler

__all__ = ('ffprobe', 'StreamProfile')

StreamProfile = Dict[str, Any]


def ffprobe(data: bytes) -> Observable[StreamProfile]:
    def subscribe(
        observer: abc.ObserverBase[StreamProfile],
        scheduler: Optional[abc.SchedulerBase] = None,
    ) -> abc.DisposableBase:
        _scheduler = scheduler or NewThreadScheduler()

        def action(scheduler: abc.SchedulerBase, state: Optional[Any] = None) -> None:
            args = [
                'ffprobe',
                '-show_streams',
                '-show_format',
                '-print_format',
                'json',
                'pipe:0',
            ]

            with Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE) as process:
                try:
                    stdout, stderr = process.communicate(data, timeout=10)
                except Exception as e:
                    process.kill()
                    process.wait()
                    observer.on_error(e)
                else:
                    profile = json.loads(stdout)
                    observer.on_next(profile)
                    observer.on_completed()

        return _scheduler.schedule(action)

    return Observable(subscribe)
