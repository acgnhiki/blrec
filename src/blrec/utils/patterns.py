from abc import ABC
from typing import TypeVar, Type, final


__all__ = 'Singleton',


_T = TypeVar('_T', bound='Singleton')


class Singleton(ABC):
    __instance = None

    @final
    def __new__(cls, *args, **kwargs):  # type: ignore
        raise SyntaxWarning(f'{cls.__name__} is a singleton!')

    @final
    @classmethod
    def get_instance(cls: Type[_T]) -> _T:
        assert cls is not Singleton and issubclass(cls, Singleton)
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance.__init__()
        return cls.__instance
