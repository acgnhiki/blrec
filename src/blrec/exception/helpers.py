import traceback


def format_exception(exc: BaseException) -> str:
    exc_info = (type(exc), exc, exc.__traceback__)
    return ''.join(traceback.format_exception(*exc_info))
