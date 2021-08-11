
from typing import Union


from .remuxer import RemuxProgress
from ..flv.metadata_injector import InjectProgress


Progress = Union[RemuxProgress, InjectProgress]
