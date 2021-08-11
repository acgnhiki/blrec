from enum import IntEnum
from datetime import datetime
from collections import OrderedDict
from typing import Any, BinaryIO, Dict, Final, List, Tuple


from .struct_io import StructWriter, StructReader


__all__ = (
    'Undefined',
    'AMFReader',
    'AMFWriter',
)


class ScriptDataValueType(IntEnum):
    NUMBER = 0
    BOOLEAN = 1
    STRING = 2
    OBJECT = 3
    MOVIE_CLIP = 4
    NULL = 5
    UNDEFINED = 6
    REFERENCE = 7
    ECMA_ARRAY = 8
    OBJECT_END_MARKER = 9
    STRICT_ARRAY = 10
    DATE = 11
    LONG_STRING = 12


Undefined: Final[object] = object()


class AMFReader:
    def __init__(self, stream: BinaryIO) -> None:
        self._reader = StructReader(stream)

    def read_value(self) -> Any:
        value_type = self._read_value_type()
        if value_type == ScriptDataValueType.NUMBER:
            return self._read_number()
        elif value_type == ScriptDataValueType.BOOLEAN:
            return self._read_boolean()
        elif value_type == ScriptDataValueType.STRING:
            return self._read_string()
        elif value_type == ScriptDataValueType.OBJECT:
            return self._read_object()
        elif value_type == ScriptDataValueType.MOVIE_CLIP:  # reserved
            raise NotImplementedError(value_type)
        elif value_type == ScriptDataValueType.NULL:
            return None
        elif value_type == ScriptDataValueType.UNDEFINED:
            return Undefined
        elif value_type == ScriptDataValueType.REFERENCE:
            raise NotImplementedError(value_type)
        elif value_type == ScriptDataValueType.ECMA_ARRAY:
            return self._read_ecma_array()
        elif value_type == ScriptDataValueType.OBJECT_END_MARKER:
            return value_type
        elif value_type == ScriptDataValueType.STRICT_ARRAY:
            return self._read_strict_array()
        elif value_type == ScriptDataValueType.DATE:
            return self._read_date()
        elif value_type == ScriptDataValueType.LONG_STRING:
            return self._read_long_string()
        else:
            raise ValueError(value_type)

    def _read_value_type(self) -> ScriptDataValueType:
        return ScriptDataValueType(self._reader.read_ui8())

    def _read_number(self) -> float:
        return self._reader.read_f64()

    def _read_boolean(self) -> bool:
        return self._reader.read_ui8() != 0

    def _read_string(self) -> str:
        size = self._reader.read_ui16()
        if size == 0:
            return ''
        data = self._reader.read(size)
        return data.decode()

    def _read_long_string(self) -> str:
        size = self._reader.read_ui32()
        if size == 0:
            return ''
        data = self._reader.read(size)
        return data.decode()

    def _read_object_property(self) -> Tuple[str, Any]:
        key = self._read_string()
        value = self.read_value()
        return key, value

    def _read_object(self) -> Dict[str, Any]:
        result = {}
        while True:
            key, value = self._read_object_property()
            if key == '' and value == ScriptDataValueType.OBJECT_END_MARKER:
                break
            result[key] = value
        return result

    def _read_ecma_array(self) -> 'OrderedDict[str, Any]':
        count = self._reader.read_ui32()
        result = OrderedDict(self._read_object())
        assert len(result) == count
        return result

    def _read_strict_array(self) -> List[Any]:
        count = self._reader.read_ui32()
        result = list(self.read_value() for _ in range(count))
        assert len(result) == count
        return result

    def _read_date(self) -> datetime:
        # the number of milliseconds
        timestamp = self._reader.read_f64() / 1000
        # reserved, should be set to 0x0000
        time_zone = self._reader.read_si16()
        assert time_zone == 0x0000
        return datetime.fromtimestamp(timestamp)


class AMFWriter:
    def __init__(self, stream: BinaryIO) -> None:
        self._writer = StructWriter(stream)

    def write_value(self, value: Any) -> None:
        if value is None:
            self._write_value_type(ScriptDataValueType.NULL)
        elif value is Undefined:
            self._write_value_type(ScriptDataValueType.UNDEFINED)
        elif isinstance(value, bool):
            self._write_value_type(ScriptDataValueType.BOOLEAN)
            self._write_boolean(value)
        elif isinstance(value, float):
            self._write_value_type(ScriptDataValueType.NUMBER)
            self._write_number(value)
        elif isinstance(value, str):
            if len(value.encode()) > 65535:  # XXX
                self._write_value_type(ScriptDataValueType.LONG_STRING)
                self._write_long_string(value)
            else:
                self._write_value_type(ScriptDataValueType.STRING)
                self._write_string(value)
        elif isinstance(value, list):
            self._write_value_type(ScriptDataValueType.STRICT_ARRAY)
            self._write_strict_array(value)
        elif isinstance(value, OrderedDict):
            self._write_value_type(ScriptDataValueType.ECMA_ARRAY)
            self._write_ecma_array(value)
        elif isinstance(value, dict):
            self._write_value_type(ScriptDataValueType.OBJECT)
            self._write_object(value)
        elif isinstance(value, datetime):
            self._write_value_type(ScriptDataValueType.DATE)
            self._write_date(value)
        else:
            raise TypeError(type(value))

    def _write_value_type(self, value_type: ScriptDataValueType) -> None:
        self._writer.write_ui8(value_type.value)

    def _write_number(self, number: float) -> None:
        self._writer.write_f64(number)

    def _write_boolean(self, boolean: bool) -> None:
        self._writer.write_ui8(int(boolean))

    def _write_string(self, string: str) -> None:
        data = string.encode()
        size = len(data)
        self._writer.write_ui16(size)
        if size > 0:
            self._writer.write(data)

    def _write_long_string(self, string: str) -> None:
        data = string.encode()
        size = len(data)
        self._writer.write_ui32(size)
        if size > 0:
            self._writer.write(data)

    def _write_object_property(self, key: str, value: Any) -> None:
        self._write_string(key)
        self.write_value(value)

    def _finalize_write_object(self) -> None:
        self._write_string('')
        self._write_value_type(ScriptDataValueType.OBJECT_END_MARKER)

    def _write_object(self, obj: Dict[str, Any]) -> None:
        for key, value in obj.items():
            self._write_object_property(key, value)
        self._finalize_write_object()

    def _write_ecma_array(self, array: 'OrderedDict[str, Any]') -> None:
        self._writer.write_ui32(len(array))
        self._write_object(array)

    def _write_strict_array(self, array: List[Any]) -> None:
        self._writer.write_ui32(len(array))
        for item in array:
            self.write_value(item)

    def _write_date(self, date_time: datetime) -> None:
        # the number of milliseconds
        self._writer.write_f64(date_time.timestamp() * 1000)
        # reserved, should be set to 0x0000
        self._writer.write_si16(0x0000)
