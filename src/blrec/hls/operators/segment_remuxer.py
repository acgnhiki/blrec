from __future__ import annotations

import io
import logging
import os
from typing import Optional, Union

import av
from reactivex import Observable, abc
from reactivex.disposable import CompositeDisposable, Disposable, SerialDisposable

from blrec.bili.live import Live

from .segment_fetcher import InitSectionData, SegmentData

__all__ = ('SegmentRemuxer',)


logger = logging.getLogger(__name__)

TRACE_REMUX_SEGMENT = bool(os.environ.get('BLREC_TRACE_REMUX_SEGMENT'))
TRACE_LIBAV = bool(os.environ.get('BLREC_TRACE_LIBAV'))
if TRACE_LIBAV:
    logging.getLogger('libav').setLevel(5)
else:
    av.logging.set_level(av.logging.FATAL)


class SegmentRemuxer:
    def __init__(self, live: Live) -> None:
        self._live = live

    def __call__(
        self, source: Observable[Union[InitSectionData, SegmentData]]
    ) -> Observable[bytes]:
        return self._remux(source)

    def _remux(
        self, source: Observable[Union[InitSectionData, SegmentData]]
    ) -> Observable[bytes]:
        def subscribe(
            observer: abc.ObserverBase[bytes],
            scheduler: Optional[abc.SchedulerBase] = None,
        ) -> abc.DisposableBase:
            disposed = False
            subscription = SerialDisposable()

            init_section_data: Optional[bytes] = None

            def reset() -> None:
                nonlocal init_section_data
                init_section_data = None

            def on_next(data: Union[InitSectionData, SegmentData]) -> None:
                nonlocal init_section_data

                if isinstance(data, InitSectionData):
                    init_section_data = data.payload
                    observer.on_next(b'')
                    return

                if init_section_data is None:
                    return

                try:
                    remuxed_data = self._remux_segemnt(init_section_data + data.payload)
                except av.FFmpegError as e:
                    logger.warning(f'Failed to remux segment: {repr(e)}', exc_info=e)
                else:
                    observer.on_next(remuxed_data)

            def dispose() -> None:
                nonlocal disposed
                disposed = True
                reset()

            subscription.disposable = source.subscribe(
                on_next, observer.on_error, observer.on_completed, scheduler=scheduler
            )

            return CompositeDisposable(subscription, Disposable(dispose))

        return Observable(subscribe)

    def _remux_segemnt(self, data: bytes, format: str = 'flv') -> bytes:
        in_file = io.BytesIO(data)
        out_file = io.BytesIO()

        with av.open(in_file) as in_container:
            with av.open(out_file, mode='w', format=format) as out_container:
                in_video_stream = in_container.streams.video[0]
                in_audio_stream = in_container.streams.audio[0]
                out_video_stream = out_container.add_stream(template=in_video_stream)
                out_audio_stream = out_container.add_stream(template=in_audio_stream)

                for packet in in_container.demux():
                    if TRACE_REMUX_SEGMENT:
                        logger.debug(repr(packet))
                    # We need to skip the "flushing" packets that `demux` generates.
                    if packet.dts is None:
                        continue
                    # We need to assign the packet to the new stream.
                    if packet.stream.type == 'video':
                        packet.stream = out_video_stream
                    elif packet.stream.type == 'audio':
                        packet.stream = out_audio_stream
                    else:
                        raise NotImplementedError(packet.stream.type)
                    out_container.mux(packet)

        return out_file.getvalue()
