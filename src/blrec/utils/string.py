import re
from typing import Optional


def snake_case(string: str) -> str:
    return re.sub(
        r'([a-z])([A-Z])', lambda m: m.group(1) + '_' + m.group(2).lower(), string
    )


def camel_case(string: str) -> str:
    words = string.split('_')
    return ''.join([words[0].casefold()] + [word.capitalize() for word in words[1:]])


def extract_uid_from_cookie(cookie: str) -> Optional[int]:
    match = re.search(r'DedeUserID=(\d+);', cookie)
    if match:
        return int(match.group(1))
    else:
        return None


def extract_buvid_from_cookie(cookie: str) -> Optional[str]:
    match = re.search(r'buvid3=([\w-]+);', cookie)
    if match:
        return match.group(1)
    else:
        return None
