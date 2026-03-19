from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass(slots=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int | None = None


@dataclass(slots=True)
class RateLimitConfig:
    max_requests: int = 1
    window_seconds: int = 1
    blocked_status_code: int = 429
    ignored_paths: set[str] = field(default_factory=set)


class RateLimitService:
    def __init__(self, config: RateLimitConfig) -> None:
        self._config = config
        self._lock = threading.Lock()
        self._requests_by_ip: dict[str, deque[float]] = {}

    def is_ignored_path(self, path: str) -> bool:
        return path in self._config.ignored_paths

    def check(self, ip: str, now: float | None = None) -> RateLimitDecision:
        now = time.monotonic() if now is None else now
        window_seconds = self._config.window_seconds
        max_requests = self._config.max_requests
        window_start = now - window_seconds

        with self._lock:
            history = self._requests_by_ip.get(ip)
            if history is None:
                self._requests_by_ip[ip] = deque([now])
                return RateLimitDecision(allowed=True)

            while history and history[0] <= window_start:
                history.popleft()

            if len(history) >= max_requests:
                retry_after = max(1, int(history[0] + window_seconds - now))
                return RateLimitDecision(
                    allowed=False,
                    retry_after_seconds=retry_after,
                )

            history.append(now)
            return RateLimitDecision(allowed=True)

    def reset_ip(self, ip: str) -> None:
        with self._lock:
            self._requests_by_ip.pop(ip, None)

    def reset_all(self) -> None:
        with self._lock:
            self._requests_by_ip.clear()
