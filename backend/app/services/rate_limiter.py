import time
from collections import defaultdict, deque
from typing import Deque

from app.core.config import settings


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._windows: dict[str, Deque[float]] = defaultdict(deque)
        self._last_prune = time.time()

    def _prune_stale_keys(self, now: float) -> None:
        # Drop empty windows periodically so long-running processes do not
        # accumulate one deque per session forever.
        if now - self._last_prune < 300:
            return
        self._last_prune = now
        stale = [key for key, window in self._windows.items() if not window or window[-1] <= now - 60]
        for key in stale:
            del self._windows[key]

    def check(self, key: str) -> bool:
        now = time.time()
        self._prune_stale_keys(now)
        window = self._windows[key]
        while window and window[0] <= now - 60:
            window.popleft()
        if len(window) >= settings.max_queries_per_minute:
            return False
        window.append(now)
        return True

    def remaining(self, key: str) -> int:
        now = time.time()
        window = self._windows[key]
        while window and window[0] <= now - 60:
            window.popleft()
        return max(0, settings.max_queries_per_minute - len(window))


rate_limiter = SlidingWindowRateLimiter()
