import struct


from .io_protocols import RandomIO


__all__ = 'StructReader', 'StructWriter'


class StructReader:
    def __init__(self, stream: RandomIO) -> None:
        self._stream = stream

    def read(self, size: int) -> bytes:
        data = self._stream.read(size)
        if len(data) != size:
            raise EOFError
        return data

    def read_ui8(self) -> int:
        return struct.unpack('B', self.read(1))[0]

    def read_ui16(self) -> int:
        return struct.unpack('>H', self.read(2))[0]

    def read_ui24(self) -> int:
        return struct.unpack('>I', b'\x00' + self.read(3))[0]

    def read_ui32(self) -> int:
        return struct.unpack('>I', self.read(4))[0]

    def read_si16(self) -> int:
        return struct.unpack('>h', self.read(2))[0]

    def read_f64(self) -> float:
        return struct.unpack('>d', self.read(8))[0]


class StructWriter:
    def __init__(self, stream: RandomIO) -> None:
        self._stream = stream

    def write(self, data: bytes) -> int:
        return self._stream.write(data)

    def write_ui8(self, number: int) -> int:
        return self.write(struct.pack('B', number))

    def write_ui16(self, number: int) -> int:
        return self.write(struct.pack('>H', number))

    def write_ui24(self, number: int) -> int:
        return self.write(struct.pack('>I', number)[1:])

    def write_ui32(self, number: int) -> int:
        return self.write(struct.pack('>I', number))

    def write_si16(self, number: int) -> int:
        return self.write(struct.pack('>h', number))

    def write_f64(self, number: float) -> int:
        return self.write(struct.pack('>d', number))
