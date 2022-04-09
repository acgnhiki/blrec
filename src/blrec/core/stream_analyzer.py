import json
import logging
from subprocess import Popen, PIPE
from typing import Dict, Any, Optional

from rx import create
from rx.core import Observable
from rx.core.typing import Observer, Scheduler, Disposable
from rx.scheduler.newthreadscheduler import NewThreadScheduler


logger = logging.getLogger(__name__)


__all__ = 'ffprobe', 'StreamProfile'


StreamProfile = Dict[str, Any]


def ffprobe(data: bytes) -> Observable:
    def subscribe(
        observer: Observer[StreamProfile],
        scheduler: Optional[Scheduler] = None,
    ) -> Disposable:
        _scheduler = scheduler or NewThreadScheduler()

        def action(scheduler, state):  # type: ignore
            args = [
                'ffprobe',
                '-show_streams',
                '-show_format',
                '-print_format',
                'json',
                'pipe:0',
            ]

            with Popen(
                args, stdin=PIPE, stdout=PIPE, stderr=PIPE
            ) as process:
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

    return create(subscribe)
