from typing import Union

from ..flv.metadata_injection import InjectingProgress
from .remux import RemuxingProgress

Progress = Union[RemuxingProgress, InjectingProgress]
