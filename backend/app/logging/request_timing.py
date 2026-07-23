from __future__ import annotations

import logging
import time
from typing import Any

from flask import g, has_request_context, request

from app.logging.request_logging import get_request_log_path

REQUEST_TIMING_LOGGER = logging.getLogger("app.request_timing")


class RequestTimingLogger:
    """Log request-scoped timing checkpoints from anywhere in request code.

    Do not pass secrets or plaintext key material in ``fields``. The fields are
    intended for step labels, IDs, source names, counts, and other safe context.
    """

    def log(self, label: str, **fields: object) -> None:
        """Log a checkpoint with elapsed time since request start."""
        now = time.perf_counter()
        duration_ms: float | None = None
        step_delta_ms: float | None = None
        extra: dict[str, Any] = {
            "timing_label": label,
            "metadata": fields or None,
        }

        if has_request_context():
            started_at = getattr(g, "request_started_at", None)
            last_timing_at = getattr(g, "request_last_timing_at", started_at)

            if started_at is not None:
                duration_ms = round((now - started_at) * 1000, 2)
                extra["duration_ms"] = duration_ms

            if last_timing_at is not None:
                step_delta_ms = round((now - last_timing_at) * 1000, 2)
                extra["step_delta_ms"] = step_delta_ms

            g.request_last_timing_at = now
            extra.update(
                {
                    "request_id": getattr(g, "request_id", None),
                    "method": request.method,
                    "path": get_request_log_path(),
                }
            )

        REQUEST_TIMING_LOGGER.debug(
            _build_message(
                label,
                duration_ms=duration_ms,
                step_delta_ms=step_delta_ms,
                fields=fields,
            ),
            extra=extra,
        )

    def checkpoint(self, label: str, **fields: object) -> None:
        """Alias for ``log`` when the call site reads better as a checkpoint."""
        self.log(label, **fields)


def _build_message(
    label: str,
    *,
    duration_ms: float | None,
    step_delta_ms: float | None,
    fields: dict[str, object],
) -> str:
    parts = [f"request_timing step={label}"]
    if duration_ms is not None:
        parts.append(f"duration_ms={duration_ms}")
    if step_delta_ms is not None:
        parts.append(f"step_delta_ms={step_delta_ms}")
    parts.extend(f"{key}={value!r}" for key, value in fields.items())
    return " ".join(parts)


request_timing = RequestTimingLogger()
