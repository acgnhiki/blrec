from __future__ import annotations

import io
from copy import deepcopy
from decimal import Decimal
from pathlib import PurePath
from typing import Optional, Tuple, Union, cast

import m3u8
from loguru import logger
from m3u8.model import InitializationSection
from reactivex import Observable, Subject, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable

from ..helpler import sequence_number_of
from .segment_dumper import SegmentDumper
from .segment_fetcher import InitSectionData, SegmentData

__all__ = ('PlaylistDumper',)


class PlaylistDumper:
    def __init__(self, segment_dumper: SegmentDumper) -> None:
        self._segment_dumper = segment_dumper

        def on_open(args: Tuple[str, int]) -> None:
            self._open_file(*args)

        def on_close(path: str) -> None:
            self._close_file()
            self._reset()

        self._segment_dumper.file_opened.subscribe(on_open)
        self._segment_dumper.file_closed.subscribe(on_close)

        self._file_opened: Subject[Tuple[str, int]] = Subject()
        self._file_closed: Subject[str] = Subject()
        self._duration_updated: Subject[float] = Subject()
        self._segments_lost: Subject[int] = Subject()

        self._reset()

    def _reset(self) -> None:
        self._path: str = ''
        self._file: Optional[io.TextIOWrapper] = None
        self._duration: Decimal = Decimal()
        self._last_segment: Optional[m3u8.Segment] = None
        self._last_seq_num: Optional[int] = None
        self._num_of_segments_lost: int = 0

    @property
    def path(self) -> str:
        return self._path

    @property
    def duration(self) -> float:
        return float(self._duration)

    @property
    def num_of_segments_lost(self) -> int:
        return self._num_of_segments_lost

    @property
    def file_opened(self) -> Observable[Tuple[str, int]]:
        return self._file_opened

    @property
    def file_closed(self) -> Observable[str]:
        return self._file_closed

    @property
    def duration_updated(self) -> Observable[float]:
        return self._duration_updated

    @property
    def segments_lost(self) -> Observable[int]:
        return self._segments_lost

    def __call__(
        self, source: Observable[Union[InitSectionData, SegmentData]]
    ) -> Observable[Union[InitSectionData, SegmentData]]:
        return self._dump(source)

    def _open_file(self, video_path: str, timestamp: int) -> None:
        path = PurePath(video_path)
        self._video_file_name = path.name
        self._path = str(path.with_suffix('.m3u8'))
        self._file = open(self._path, 'wt', encoding='utf8')  # type: ignore
        logger.debug(f'Opened file: {self._path}')
        self._file_opened.on_next((self._path, timestamp))
        self._header_dumped = False

    def _close_file(self) -> None:
        if self._file is not None and not self._file.closed:
            self._file.write('#EXT-X-ENDLIST')
            self._file.close()
            logger.debug(f'Closed file: {self._path}')
            self._file_closed.on_next(self._path)

    def _dump_header(self, item: InitSectionData) -> None:
        if self._header_dumped:
            return
        playlist: m3u8.M3U8 = deepcopy(item.segment.custom_parser_values['playlist'])
        playlist.segments.clear()
        playlist.is_endlist = False
        assert self._file is not None
        self._file.write(playlist.dumps())
        self._file.flush()
        self._header_dumped = True

    def _dump_segment(self, init_item: InitSectionData, item: SegmentData) -> None:
        seg = self._make_segment(
            item.segment,
            self._video_file_name,
            init_section_byterange=f'{len(init_item)}@{init_item.offset}',
            segment_byterange=f'{len(item)}@{item.offset}',
        )

        curr_seq_num = sequence_number_of(item.segment.uri)
        if self._last_seq_num is not None:
            if self._last_seq_num + 1 != curr_seq_num:
                seg.discontinuity = True
            if self._last_seq_num + 1 < curr_seq_num:
                self._num_of_segments_lost += curr_seq_num - self._last_seq_num - 1
                self._segments_lost.on_next(self._num_of_segments_lost)

        assert self._file is not None
        self._file.write(seg.dumps(self._last_segment) + '\n')
        self._file.flush()

        self._last_segment = seg
        self._last_seq_num = curr_seq_num

    def _make_segment(
        self,
        segment: m3u8.Segment,
        uri: str,
        init_section_byterange: str,
        segment_byterange: str,
    ) -> m3u8.Segment:
        seg = deepcopy(segment)
        if init_section := getattr(seg, 'init_section', None):
            init_section = cast(InitializationSection, init_section)
            init_section.uri = uri
            init_section.base_uri = ''
            init_section.byterange = init_section_byterange
        seg.uri = uri
        seg.byterange = segment_byterange
        seg.title += '|' + segment.uri
        return seg

    def _update_duration(self, segment: m3u8.Segment) -> None:
        self._duration += Decimal(str(segment.duration))
        self._duration_updated.on_next(float(self._duration))

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
                try:
                    if isinstance(item, InitSectionData):
                        self._dump_header(item)
                        last_init_item = item
                    else:
                        assert last_init_item is not None
                        self._dump_segment(last_init_item, item)
                        self._update_duration(item.segment)
                except Exception as e:
                    self._close_file()
                    self._reset()
                    observer.on_error(e)
                else:
                    observer.on_next(item)

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
