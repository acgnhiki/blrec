import io
from pathlib import PurePath
from typing import Callable, Optional, Tuple, Union

import attr
from loguru import logger
from reactivex import Observable, Subject, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable

from blrec.utils.ffprobe import ffprobe

from .segment_fetcher import InitSectionData, SegmentData

__all__ = ('SegmentDumper',)


class SegmentDumper:
    def __init__(
        self, path_provider: Callable[[Optional[int]], Tuple[str, int]]
    ) -> None:
        self._path_provider = path_provider
        self._file_opened: Subject[Tuple[str, int]] = Subject()
        self._file_closed: Subject[str] = Subject()
        self._reset()

    def _reset(self) -> None:
        self._path: str = ''
        self._file: Optional[io.BufferedWriter] = None
        self._filesize: int = 0

    @property
    def path(self) -> str:
        return self._path

    @property
    def filesize(self) -> int:
        return self._filesize

    @property
    def file_opened(self) -> Observable[Tuple[str, int]]:
        return self._file_opened

    @property
    def file_closed(self) -> Observable[str]:
        return self._file_closed

    def __call__(
        self, source: Observable[Union[InitSectionData, SegmentData]]
    ) -> Observable[Union[InitSectionData, SegmentData]]:
        return self._dump(source)

    def _open_file(self) -> None:
        path, timestamp = self._path_provider()
        self._path = str(PurePath(path).with_suffix('.m4s'))
        self._file = open(self._path, 'wb')  # type: ignore
        logger.debug(f'Opened file: {self._path}')
        self._file_opened.on_next((self._path, timestamp))

    def _close_file(self) -> None:
        if self._file is not None and not self._file.closed:
            self._file.close()
            logger.debug(f'Closed file: {self._path}')
            self._file_closed.on_next(self._path)

    def _write_data(self, item: Union[InitSectionData, SegmentData]) -> Tuple[int, int]:
        assert self._file is not None
        offset = self._file.tell()
        size = self._file.write(item.payload)
        assert size == len(item)
        return offset, size

    def _update_filesize(self, size: int) -> None:
        self._filesize += size

    def _is_redundant(
        self, prev_init_item: Optional[InitSectionData], curr_init_item: InitSectionData
    ) -> bool:
        return (
            prev_init_item is not None
            and curr_init_item.payload == prev_init_item.payload
        )

    def _must_split_file(
        self, prev_init_item: Optional[InitSectionData], curr_init_item: InitSectionData
    ) -> bool:
        if prev_init_item is None:
            curr_profile = ffprobe(curr_init_item.payload)
            logger.debug(f'current init section profile: {curr_profile}')
            return True

        prev_profile = ffprobe(prev_init_item.payload)
        logger.debug(f'previous init section profile: {prev_profile}')
        curr_profile = ffprobe(curr_init_item.payload)
        logger.debug(f'current init section profile: {curr_profile}')

        if prev_init_item.payload == curr_init_item.payload:
            logger.debug('the current init section is identical to the previous one')
            return False

        prev_video_profile = prev_profile['streams'][0]
        prev_audio_profile = prev_profile['streams'][1]
        assert prev_video_profile['codec_type'] == 'video'
        assert prev_audio_profile['codec_type'] == 'audio'

        curr_video_profile = curr_profile['streams'][0]
        curr_audio_profile = curr_profile['streams'][1]
        assert curr_video_profile['codec_type'] == 'video'
        assert curr_audio_profile['codec_type'] == 'audio'

        if (
            prev_video_profile['codec_name'] != curr_video_profile['codec_name']
            or prev_video_profile['width'] != curr_video_profile['width']
            or prev_video_profile['height'] != curr_video_profile['height']
            or prev_video_profile['coded_width'] != curr_video_profile['coded_width']
            or prev_video_profile['coded_height'] != curr_video_profile['coded_height']
        ):
            logger.warning('Video parameters changed')

        if (
            prev_audio_profile['codec_name'] != curr_audio_profile['codec_name']
            or prev_audio_profile['channels'] != curr_audio_profile['channels']
            or prev_audio_profile['sample_rate'] != curr_audio_profile['sample_rate']
            or prev_audio_profile.get('bit_rate') != curr_audio_profile.get('bit_rate')
        ):
            logger.warning('Audio parameters changed')

        logger.debug(
            'must split the file '
            'because the current init section is not identical to the previous one'
        )
        return True

    def _need_split_file(self, item: Union[InitSectionData, SegmentData]) -> bool:
        return item.segment.custom_parser_values.get('split', False)

    def _dump(
        self, source: Observable[Union[InitSectionData, SegmentData]]
    ) -> Observable[Union[InitSectionData, SegmentData]]:
        def subscribe(
            observer: abc.ObserverBase[Union[InitSectionData, SegmentData]],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            disposed = False
            subscription = SerialDisposable()
            last_init_item: Optional[InitSectionData] = None

            def on_next(item: Union[InitSectionData, SegmentData]) -> None:
                nonlocal last_init_item
                split_file = False

                if isinstance(item, InitSectionData):
                    if self._is_redundant(last_init_item, item):
                        return
                    split_file = self._must_split_file(last_init_item, item)
                    last_init_item = item

                if not split_file:
                    split_file = self._need_split_file(item)

                if split_file:
                    self._close_file()
                    self._reset()
                    self._open_file()

                try:
                    if split_file and not isinstance(item, InitSectionData):
                        assert last_init_item is not None
                        offset, size = self._write_data(last_init_item)
                        self._update_filesize(size)
                        observer.on_next(attr.evolve(last_init_item, offset=offset))

                    offset, size = self._write_data(item)
                    self._update_filesize(size)
                    observer.on_next(attr.evolve(item, offset=offset))
                except Exception as e:
                    logger.error(f'Failed to write data: {repr(e)}')
                    self._close_file()
                    self._reset()
                    observer.on_error(e)

            def on_completed() -> None:
                self._close_file()
                self._reset()
                observer.on_completed()

            def on_error(e: Exception) -> None:
                self._close_file()
                self._reset()
                observer.on_error(e)

            def dispose() -> None:
                nonlocal disposed
                nonlocal last_init_item
                disposed = True
                last_init_item = None
                self._close_file()
                self._reset()

            subscription.disposable = source.subscribe(
                on_next, on_error, on_completed, scheduler=scheduler
            )

            return CompositeDisposable(subscription, Disposable(dispose))

        return Observable(subscribe)
