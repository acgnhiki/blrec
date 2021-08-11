import traceback


def format_exception(exc: BaseException) -> str:
    exc_info = (type(exc), exc, exc.__traceback__)
    errmsg = 'Unhandled exception in event loop\n'
    errmsg += ''.join(traceback.format_exception(*exc_info))
    return errmsg
