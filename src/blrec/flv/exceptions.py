
class FlvDataError(ValueError):
    ...


class InvalidFlvHeaderError(FlvDataError):
    ...


class InvalidFlvTagError(FlvDataError):
    ...


class FlvStreamCorruptedError(FlvDataError):
    ...


class FlvFileCorruptedError(FlvDataError):
    ...


class AudioParametersChanged(Exception):
    ...


class VideoParametersChanged(Exception):
    ...


class FileSizeOverLimit(Exception):
    ...


class DurationOverLimit(Exception):
    ...


class CutStream(Exception):
    ...
