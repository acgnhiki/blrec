import os

__all__ = ('name_of', 'sequence_number_of')


def name_of(uri: str) -> str:
    name, _ext = os.path.splitext(uri)
    return name


def sequence_number_of(uri: str) -> int:
    return int(name_of(uri))
