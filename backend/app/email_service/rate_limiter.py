"""In-memory rate limiter for email sends."""

from __future__ import annotations

import threading
import time
from collections import deque

from app.core.config import EmailSettings
from app.email_service.exceptions import EmailRateLimitError


class EmailRateLimiter:
    """Enforce per-recipient cooldowns and a global send rate.

    This class does not depend on Flask, SQLAlchemy, or AWS.
    """

    def __init__(self, settings: EmailSettings) -> None:
        self._cooldown_seconds = settings.recipient_cooldown_seconds
        self._global_limit = settings.global_rate_limit
        self._global_window = settings.global_rate_window_seconds

        self._lock = threading.Lock()
        self._last_send: dict[tuple[str, str], float] = {}
        self._global_sends: deque[float] = deque()

    def check(self, *, recipient: str, email_type: str) -> None:
        """Raise ``EmailRateLimitError`` if either limit is exceeded."""
        now = time.monotonic()
        key = (recipient.lower(), email_type)

        with self._lock:
            last = self._last_send.get(key)
            if last is not None:
                elapsed = now - last
                if elapsed < self._cooldown_seconds:
                    retry_after = int(self._cooldown_seconds - elapsed) + 1
                    raise EmailRateLimitError(
                        f"Recipient cooldown active for {email_type}.",
                        retry_after_seconds=retry_after,
                    )

            window_start = now - self._global_window
            while self._global_sends and self._global_sends[0] <= window_start:
                self._global_sends.popleft()

            if len(self._global_sends) >= self._global_limit:
                retry_after = max(
                    1, int(self._global_sends[0] + self._global_window - now)
                )
                raise EmailRateLimitError(
                    "Global email send rate exceeded.",
                    retry_after_seconds=retry_after,
                )

    def record(self, *, recipient: str, email_type: str) -> None:
        """Record a successful send for both rate-limit buckets."""
        now = time.monotonic()
        key = (recipient.lower(), email_type)

        with self._lock:
            self._last_send[key] = now
            self._global_sends.append(now)
