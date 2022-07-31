from __future__ import annotations

import io
import logging
import os
from copy import deepcopy
from decimal import Decimal
from typing import Callable, Optional, Tuple

import m3u8
from reactivex import Observable, Subject, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable

__all__ = ('PlaylistDumper',)

logger = logging.getLogger(__name__)


class PlaylistDumper:
    def __init__(self, path_provider: Callable[..., Tuple[str, int]]) -> None:
        self._path_provider = path_provider
        self._file_opened: Subject[Tuple[str, int]] = Subject()
        self._file_closed: Subject[str] = Subject()
        self._reset()

    def _reset(self) -> None:
        self._path: str = ''
        self._file: Optional[io.TextIOWrapper] = None
        self._duration: Decimal = Decimal()

    @property
    def path(self) -> str:
        return self._path

    @property
    def duration(self) -> float:
        return float(self._duration)

    @property
    def file_opened(self) -> Observable[Tuple[str, int]]:
        return self._file_opened

    @property
    def file_closed(self) -> Observable[str]:
        return self._file_closed

    def __call__(self, source: Observable[m3u8.M3U8]) -> Observable[m3u8.Segment]:
        return self._dump(source)

    def _open_file(self) -> None:
        path, timestamp = self._path_provider()
        root, ext = os.path.splitext(path)
        os.makedirs(root, exist_ok=True)
        self._path = os.path.join(root, 'index.m3u8')
        self._file = open(self._path, 'wt', encoding='utf8')  # type: ignore
        logger.debug(f'Opened file: {self._path}')
        self._file_opened.on_next((self._path, timestamp))

    def _close_file(self) -> None:
        if self._file is not None and not self._file.closed:
            self._file.write('#EXT-X-ENDLIST')
            self._file.close()
            logger.debug(f'Closed file: {self._path}')
            self._file_closed.on_next(self._path)

    def _name_of(self, uri: str) -> str:
        name, ext = os.path.splitext(uri)
        return name

    def _sequence_number_of(self, uri: str) -> int:
        return int(self._name_of(uri))

    def _replace_uri(self, segment: m3u8.Segment) -> m3u8.Segment:
        copied_seg = deepcopy(segment)
        if init_section := getattr(copied_seg, 'init_section', None):
            init_section.uri = f'segments/{init_section.uri}'
        uri = segment.uri
        name = self._name_of(uri)
        copied_seg.uri = 'segments/%s/%s' % (name[:-3], uri)
        return copied_seg

    def _replace_all_uri(self, playlist: m3u8.M3U8) -> m3u8.M3U8:
        copied_playlist = deepcopy(playlist)
        copied_playlist.segments = m3u8.SegmentList(
            self._replace_uri(s) for s in copied_playlist.segments
        )
        return copied_playlist

    def _update_duration(self, segment: m3u8.Segment) -> None:
        self._duration += Decimal(str(segment.duration))

    def _dump(self, source: Observable[m3u8.M3U8]) -> Observable[m3u8.Segment]:
        def subscribe(
            observer: abc.ObserverBase[m3u8.Segment],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            disposed = False
            subscription = SerialDisposable()

            last_segment: Optional[m3u8.Segment] = None
            last_sequence_number: Optional[int] = None
            first_playlist_dumped: bool = False

            self._close_file()
            self._reset()

            def on_next(playlist: m3u8.M3U8) -> None:
                nonlocal last_sequence_number, last_segment, first_playlist_dumped

                if playlist.is_endlist:
                    logger.debug('Playlist ended')

                try:
                    if not first_playlist_dumped:
                        self._close_file()
                        self._reset()
                        self._open_file()
                        assert self._file is not None
                        playlist.is_endlist = False
                        self._file.write(self._replace_all_uri(playlist).dumps())
                        self._file.flush()
                        for seg in playlist.segments:
                            observer.on_next(seg)
                            self._update_duration(seg)
                            last_segment = seg
                            last_sequence_number = self._sequence_number_of(seg.uri)
                        first_playlist_dumped = True
                        logger.debug('The first playlist has been dumped')
                        return

                    assert self._file is not None
                    for seg in playlist.segments:
                        num = self._sequence_number_of(seg.uri)
                        discontinuity = False
                        if last_sequence_number is not None:
                            if last_sequence_number >= num:
                                continue
                            if last_sequence_number + 1 != num:
                                logger.warning(
                                    'Segments discontinuous: '
                                    f'last sequence number: {last_sequence_number}, '
                                    f'current sequence number: {num}'
                                )
                                discontinuity = True
                        new_seg = self._replace_uri(seg)
                        new_seg.discontinuity = discontinuity
                        new_last_seg = self._replace_uri(last_segment)
                        self._file.write(new_seg.dumps(new_last_seg) + '\n')
                        observer.on_next(seg)
                        self._update_duration(seg)
                        last_segment = seg
                        last_sequence_number = num
                except Exception as e:
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
                nonlocal last_segment, last_sequence_number
                disposed = True
                last_segment = None
                last_sequence_number = None
                self._close_file()
                self._reset()

            subscription.disposable = source.subscribe(
                on_next, on_error, on_completed, scheduler=scheduler
            )

            return CompositeDisposable(subscription, Disposable(dispose))

        return Observable(subscribe)
