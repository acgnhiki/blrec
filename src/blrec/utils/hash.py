import os
import zlib
import hashlib
from typing import Final, Union

from tqdm import tqdm


__all__ = 'cksum', 'md5sum', 'sha1sum'


CHUNK_SIZE: Final[int] = 8192


def cksum(data_or_path: Union[bytes, str], nopbar: bool = True) -> str:
    """Compute CRC32 checksum.

    data_or_path: can be bytes of binary data or a file path.
    """
    if isinstance(data_or_path, bytes):
        value = zlib.crc32(data_or_path, 0)
        return hex(value & 0xffffffff)[2:]

    with open(data_or_path, 'rb') as f, tqdm(
        desc='Computing CRC32',
        total=os.path.getsize(data_or_path),
        unit='B', unit_scale=True, unit_divisor=1024,
        disable=nopbar,
    ) as pbar:
        value = 0

        while True:
            data = f.read(CHUNK_SIZE)

            if not data:
                break

            value = zlib.crc32(data, value)
            pbar.update(len(data))

    return hex(value & 0xffffffff)[2:]


def md5sum(data_or_path: Union[bytes, str], nopbar: bool = True) -> str:
    """Compute MD5 message digest.

    data_or_path: can be bytes of binary data or a file path.
    """
    if isinstance(data_or_path, bytes):
        return hashlib.md5(data_or_path).hexdigest()

    with open(data_or_path, 'rb') as f, tqdm(
        desc='Computing MD5',
        total=os.path.getsize(data_or_path),
        postfix=os.path.basename(data_or_path),
        unit='B', unit_scale=True, unit_divisor=1024,
        disable=nopbar,
    ) as pbar:
        m = hashlib.md5()

        while True:
            data = f.read(CHUNK_SIZE)

            if not data:
                break

            m.update(data)
            pbar.update(len(data))

        md5 = m.hexdigest()

    return md5


def sha1sum(data_or_path: Union[bytes, str], nopbar: bool = True) -> str:
    """Compute SHA1 message digest.

    data_or_path: can be bytes of binary data or a file path.
    """
    if isinstance(data_or_path, bytes):
        return hashlib.sha1(data_or_path).hexdigest()

    with open(data_or_path, 'rb') as f, tqdm(
        desc='Computing SHA1',
        total=os.path.getsize(data_or_path),
        postfix=os.path.basename(data_or_path),
        unit='B', unit_scale=True, unit_divisor=1024,
        disable=nopbar,
    ) as pbar:
        s = hashlib.sha1()

        while True:
            data = f.read(CHUNK_SIZE)

            if not data:
                break

            s.update(data)
            pbar.update(len(data))

        sha1 = s.hexdigest()

    return sha1
