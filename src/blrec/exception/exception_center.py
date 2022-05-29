from reactivex import Observable, Subject

from ..utils.patterns import Singleton

__all__ = ('ExceptionCenter',)


class ExceptionCenter(Singleton):
    def __init__(self) -> None:
        super().__init__()
        self._source: Subject[BaseException] = Subject()

    @property
    def exceptions(self) -> Observable[BaseException]:
        return self._source

    def submit(self, exc: BaseException) -> None:
        self._source.on_next(exc)
