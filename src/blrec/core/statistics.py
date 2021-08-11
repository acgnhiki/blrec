import time


__all__ = 'StatisticsCalculator',


class StatisticsCalculator:
    def __init__(self, interval: float = 1.0) -> None:
        self._interval = interval
        self._frozen = True

        self._count: int = 0
        self._rate: float = 0.0
        self._start_time: float = 0.0
        self._last_time: float = 0.0
        self._last_count: int = 0
        self._elapsed: float = 0.0

    @property
    def count(self) -> int:
        return self._count

    @property
    def rate(self) -> float:
        if self._frozen:
            return self._rate

        curr_time = time.monotonic()
        time_delta = curr_time - self._last_time

        if time_delta >= self._interval:
            count_delta = self._count - self._last_count
            self._rate = count_delta / time_delta

            self._last_time = curr_time
            self._last_count = self._count

        return self._rate

    @property
    def elapsed(self) -> float:
        if not self._frozen:
            self._elapsed = time.monotonic() - self._start_time
        return self._elapsed

    def freeze(self) -> None:
        self._frozen = True

    def reset(self) -> None:
        self._count = self._last_count = 0
        self._start_time = self._last_time = time.monotonic()
        self._rate = 0.0
        self._elapsed = 0.0

        self._frozen = False

    def submit(self, count: int) -> None:
        if not self._frozen:
            self._count += count
