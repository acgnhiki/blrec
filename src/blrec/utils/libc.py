from contextlib import suppress
from ctypes import cdll
from ctypes.util import find_library

lib_name = find_library('c')
if not lib_name:
    libc = None
else:
    libc = cdll.LoadLibrary(lib_name)


def malloc_trim(pad: int) -> bool:
    """Release free memory from the heap"""
    assert pad >= 0, 'pad must be >= 0'
    if libc is None:
        return False
    with suppress(Exception):
        return libc.malloc_trim(pad) == 1
