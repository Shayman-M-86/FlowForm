"""Attribute policy for exported trace data.

Trace attributes are an outbound data boundary: they are exported to Tempo and
retained outside the app. Only allowlisted, bounded, non-identifying values are
ever recorded. The unsafe-field vocabulary is shared with
``app.logging.sensitive_data`` so trace and log policies cannot drift apart.
"""

from __future__ import annotations

import logging
import math

from app.logging.sensitive_data import _is_sensitive_key
from app.tracing.vocabulary import (
    ALLOWED_FIELDS,
    FIELD_PREFIX,
    MAX_ABS_INT,
    MAX_FIELDS,
    MAX_SEQUENCE_LENGTH,
    MAX_STRING_LENGTH,
    AttrValue,
    Scalar,
)

# Policy violations are always dropped, never raised: telemetry must not break a
# live request. They are logged at WARNING so a mislabelled field or name is
# visible in dev and prod alike, but throttled so a hot-loop offender cannot
# flood the logs (and cannot recurse back through tracing).
_diag = logging.getLogger("app.tracing")
_LOG_INTERVAL = 1000
_drop_count = 0


def reject(reason: str) -> None:
    """Drop a policy-violating value and log it (throttled) at WARNING."""
    global _drop_count
    if _drop_count % _LOG_INTERVAL == 0:
        _diag.warning("tracing policy drop: %s", reason)
    _drop_count += 1


def normalize_scalar(value: object) -> Scalar | None:
    """Return an OTLP-safe scalar, or ``None`` to drop it."""
    # bool is an int subclass; check it first so True/False stay booleans.
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value if abs(value) <= MAX_ABS_INT else None
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, str):
        return value[:MAX_STRING_LENGTH]
    return None


def normalize_sequence(value: list[object] | tuple[object, ...]) -> AttrValue | None:
    """Return a short, type-homogeneous sequence of scalars, or ``None`` to drop it.

    OTLP forbids mixed-type sequences, so a list whose scalars are not all the
    same concrete type is dropped whole. bool is bucketed apart from int so
    ``[True, 1]`` is rejected rather than silently coerced.
    """
    scalars: list[Scalar] = []
    for item in value[:MAX_SEQUENCE_LENGTH]:
        normalized = normalize_scalar(item)
        if normalized is None:
            return None  # one unusable element drops the whole sequence
        scalars.append(normalized)
    if len({type(item) for item in scalars}) > 1:
        return None
    # Runtime-homogeneous, but the checker can't derive that from the set()
    # comparison above, so it can't match one of AttrValue's per-type sequences.
    return scalars  # type: ignore[return-value]


def normalize_value(value: object) -> AttrValue | None:
    """Return an OTLP-safe attribute value, or ``None`` to drop it."""
    scalar = normalize_scalar(value)
    if scalar is not None:
        return scalar
    # str is handled by normalize_scalar; only real sequences remain here.
    if isinstance(value, (list, tuple)):
        return normalize_sequence(value)
    return None


def filter_fields(fields: dict[str, object]) -> dict[str, AttrValue]:
    """Allowlist, normalize, and ``flowform.``-prefix caller-supplied fields."""
    result: dict[str, AttrValue] = {}
    for name, raw in fields.items():
        if len(result) >= MAX_FIELDS:
            break
        if raw is None:
            continue
        if name not in ALLOWED_FIELDS or _is_sensitive_key(name):
            reject(f"field {name!r} not allowed")
            continue
        value = normalize_value(raw)
        if value is None:
            reject(f"field {name!r} has unsupported value")
            continue
        result[f"{FIELD_PREFIX}{name}"] = value
    return result
