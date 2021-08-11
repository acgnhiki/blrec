from __future__ import annotations

from bitarray import bitarray
from bitarray.util import ba2int


__all__ = 'BitsReader',


class BitsReader:
    def __init__(self, bits: bitarray) -> None:
        self._bits = bits
        self._ptr = 0

    def read_bits_as_int(self, n: int) -> int:
        return ba2int(self.read_bits(n))

    def read_bits(self, n: int) -> bitarray:
        result = self.next_bits(n)
        self._ptr += n
        return result

    def next_bits(self, n: int) -> bitarray:
        assert n >= 0
        if n == 0:
            return bitarray('0')
        return self._bits[self._ptr:self._ptr + n]
