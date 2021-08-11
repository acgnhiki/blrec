
from enum import Enum


class ProcessStatus(Enum):
    WAITING = 'waiting'
    REMUXING = 'remuxing'
    INJECTING = 'injecting'

    def __str__(self) -> str:
        return self.value


class DeleteStrategy(Enum):
    AUTO = 'auto'
    NEVER = 'never'

    def __str__(self) -> str:
        return self.value

    # workaround for value serialization
    def __repr__(self) -> str:
        return str(self)
