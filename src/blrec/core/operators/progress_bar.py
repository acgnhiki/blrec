from __future__ import annotations

import logging
from typing import Optional

from reactivex import Observable, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable
from tqdm import tqdm

from ...bili.live import Live
from ...flv.operators.typing import FLVStream, FLVStreamItem

__all__ = ('ProgressBar',)


logger = logging.getLogger(__name__)


class ProgressBar:
    def __init__(self, live: Live) -> None:
        self._live = live
        self._pbar: Optional[tqdm] = None

    def update_bar_info(self) -> None:
        if self._pbar is not None:
            self._pbar.set_postfix_str(self._make_pbar_postfix())

    def __call__(self, source: FLVStream) -> FLVStream:
        return self._progress(source)

    def _progress(self, source: FLVStream) -> FLVStream:
        def subscribe(
            observer: abc.ObserverBase[FLVStreamItem],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            subscription = SerialDisposable()

            self._pbar = tqdm(
                desc='Recording',
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                postfix=self._make_pbar_postfix(),
            )

            def on_next(item: FLVStreamItem) -> None:
                if self._pbar is not None:
                    self._pbar.update(len(item))
                observer.on_next(item)

            def on_completed() -> None:
                if self._pbar is not None:
                    self._pbar.close()
                    self._pbar = None
                observer.on_completed()

            def dispose() -> None:
                if self._pbar is not None:
                    self._pbar.close()
                    self._pbar = None

            subscription.disposable = source.subscribe(
                on_next, observer.on_error, on_completed, scheduler=scheduler
            )

            return CompositeDisposable(subscription, Disposable(dispose))

        return Observable(subscribe)

    def _make_pbar_postfix(self) -> str:
        return '{room_id} - {user_name}: {room_title}'.format(
            room_id=self._live.room_info.room_id,
            user_name=self._live.user_info.name,
            room_title=self._live.room_info.title,
        )
