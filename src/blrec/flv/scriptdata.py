from io import BytesIO
from typing import Any, BinaryIO, Dict, Mapping, TypedDict


from .amf import AMFReader, AMFWriter


__all__ = (
    'load',
    'loads',
    'dump',
    'dumps',

    'ScriptData',

    'ScriptDataParser',
    'ScriptDataDumper',
)


class ScriptData(TypedDict):
    name: str
    value: Dict[str, Any]


class ScriptDataParser:
    def __init__(self, stream: BinaryIO) -> None:
        self._reader = AMFReader(stream)

    def parse(self) -> ScriptData:
        name = self._parse_name()
        value = self._parse_value()
        return ScriptData(name=name, value=value)

    def _parse_name(self) -> str:
        value = self._reader.read_value()
        assert isinstance(value, str)
        return value

    def _parse_value(self) -> Dict[str, Any]:
        value = self._reader.read_value()
        assert isinstance(value, dict)
        return value


class ScriptDataDumper:
    def __init__(self, stream: BinaryIO) -> None:
        self._writer = AMFWriter(stream)

    def dump(self, script_data: ScriptData) -> None:
        self._dump_name(script_data['name'])
        self._dump_value(script_data['value'])

    def _dump_name(self, name: str) -> None:
        self._writer.write_value(name)

    def _dump_value(self, value: Mapping[str, Any]) -> None:
        self._writer.write_value(value)


def load(data: bytes) -> ScriptData:
    return loads(BytesIO(data))


def loads(stream: BinaryIO) -> ScriptData:
    return ScriptDataParser(stream).parse()


def dump(script_data: ScriptData) -> bytes:
    stream = BytesIO()
    dumps(script_data, stream)
    return stream.getvalue()


def dumps(script_data: ScriptData, stream: BinaryIO) -> None:
    ScriptDataDumper(stream).dump(script_data)
