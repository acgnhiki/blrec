from __future__ import annotations

from typing import Optional

from reactivex import Observable, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable
from tqdm import tqdm

from .typing import FLVStream, FLVStreamItem

__all__ = ('ProgressBar',)


class ProgressBar:
    def __init__(
        self,
        desc: str,
        postfix: Optional[str] = None,
        total: Optional[int] = None,
        disable: Optional[bool] = False,
    ) -> None:
        self._desc = desc
        self._postfix = postfix
        self._total = total
        self._disable = disable
        self._pbar: Optional[tqdm] = None

    def __call__(self, source: FLVStream) -> FLVStream:
        return self._progress(source)

    def _progress(self, source: FLVStream) -> FLVStream:
        def subscribe(
            observer: abc.ObserverBase[FLVStreamItem],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            subscription = SerialDisposable()

            self._pbar = tqdm(
                disable=self._disable,
                desc=self._desc,
                total=self._total,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                postfix=self._postfix,
            )
            self._pbar.disable

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
