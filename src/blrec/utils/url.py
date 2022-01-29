from urllib.parse import urlparse, urlunparse
from typing import Literal


def ensure_scheme(url: str, scheme: Literal['http', 'https']) -> str:
    return urlunparse(urlparse(url)._replace(scheme=scheme))
