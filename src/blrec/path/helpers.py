import os
from pathlib import PurePath


__all__ = (
    'file_exists',
    'create_file',
    'danmaku_path',
    'extra_metadata_path',
)


def file_exists(path: str) -> bool:
    return os.path.isfile(path)


def create_file(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'x'):
        pass


def danmaku_path(video_path: str) -> str:
    return str(PurePath(video_path).with_suffix('.xml'))


def extra_metadata_path(video_path: str) -> str:
    return video_path + '.meta.json'
