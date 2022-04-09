
from enum import Enum


class PostprocessorStatus(Enum):
    WAITING = 'waiting'
    REMUXING = 'remuxing'
    INJECTING = 'injecting'

    def __str__(self) -> str:
        return self.value


class DeleteStrategy(Enum):
    AUTO = 'auto'
    SAFE = 'safe'
    NEVER = 'never'

    def __str__(self) -> str:
        return self.value

    # workaround for value serialization
    def __repr__(self) -> str:
        return str(self)
