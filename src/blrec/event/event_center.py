from reactivex import Observable, Subject

from ..utils.patterns import Singleton
from .typing import Event

__all__ = ('EventCenter',)


class EventCenter(Singleton):
    def __init__(self) -> None:
        super().__init__()
        self._source: Subject[Event] = Subject()

    @property
    def events(self) -> Observable[Event]:
        return self._source

    def submit(self, event: Event) -> None:
        self._source.on_next(event)
