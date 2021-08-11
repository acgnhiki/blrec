
from rx.subject import Subject
from rx.core import Observable

from .typing import Event
from ..utils.patterns import Singleton


__all__ = 'EventCenter',


class EventCenter(Singleton):
    def __init__(self) -> None:
        super().__init__()
        self._source = Subject()

    @property
    def events(self) -> Observable:
        return self._source

    def submit(self, event: Event) -> None:
        self._source.on_next(event)
