"""The fixed vocabulary of FlowForm's business traces.

Three small, self-contained concerns that only this package uses and that never
change by environment: the value types exported as span attributes, the naming
rules for actions/events, and the local constants (tracer name, allowlist,
bounds). They are grouped here rather than split across three one-screen files.

Anything environment-driven (enable, endpoint, sampling, defer, strict) lives in
``TracingSettings`` in :mod:`app.core.config`, not here.
"""

from __future__ import annotations

from collections.abc import Sequence

# --- Value types (mirror OpenTelemetry's AttributeValue) -------------------

type Scalar = str | bool | int | float
type AttrValue = Scalar | Sequence[str] | Sequence[bool] | Sequence[int] | Sequence[float]

# --- Constants -------------------------------------------------------------

# Instrumentation scope for FlowForm-owned business spans, distinct from the
# auto-instrumented Flask/SQLAlchemy scopes.
TRACER_NAME = "flowform.business"

# Shared prefix so business telemetry is trivially separable from library
# telemetry, and so a mislabelled span still records under a known name.
FIELD_PREFIX = "flowform."
FALLBACK_ACTION = f"{FIELD_PREFIX}action.invalid"

# Bounds on exported attribute values. Trace attributes leave the process and
# are retained in Tempo, so every value is length- and range-capped.
MAX_FIELDS = 24
MAX_STRING_LENGTH = 256
MAX_SEQUENCE_LENGTH = 32
MAX_ABS_INT = 2**53  # stay within the lossless float range OTLP exporters use

# Allowlisted attribute names. FlowForm-owned; no raw identifiers. Extend only
# with a documented operational need (see the tracing plan).
ALLOWED_FIELDS = frozenset(
    {
        "outcome",
        "checkpoint",
        "question_type",
        "submission_mode",
        "validation_error_count",
        "answer_count",
        "version_number",
        "completion_state",
        "authentication_method",
    }
)

# --- Name rules ------------------------------------------------------------

# Actions are ``<domain>.<entity>.<verb>``; events are ``flowform.<domain>.<event>``.
# Names are structural labels only and must never carry runtime values.
_NAME_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz._")


def valid_action_name(name: str) -> bool:
    return (
        3 <= len(name) <= 64
        and "." in name
        and set(name) <= _NAME_CHARS
        and not name.startswith(".")
        and not name.endswith(".")
    )


def valid_event_name(name: str) -> bool:
    return name.startswith(FIELD_PREFIX) and valid_action_name(name)
