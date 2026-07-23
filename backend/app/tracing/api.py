"""FlowForm-owned business observability API over OpenTelemetry.

Application code uses a small, safe surface::

    from app import tracing

    @tracing.action("submission.answer.save")
    def save_answer(...):
        tracing.fields(outcome="accepted", question_type="single_choice")
        tracing.event("flowform.submission.validation_completed", outcome="rejected")

Provider, exporter, and instrumentation lifecycle live in
:mod:`app.tracing.extension` / :mod:`app.tracing.provider`. Attribute policy
lives in :mod:`app.tracing.policy`; the trace vocabulary (value types, name
rules, constants) in :mod:`app.tracing.vocabulary`.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Protocol, TypeVar

from opentelemetry import trace
from opentelemetry.trace import Span

from app.tracing.policy import filter_fields, reject
from app.tracing.vocabulary import (
    FALLBACK_ACTION,
    TRACER_NAME,
    valid_action_name,
    valid_event_name,
)

_F = TypeVar("_F", bound=Callable[..., object])


class SpanScope(AbstractContextManager[Span], Protocol):
    """A span handle usable as either a ``with`` block or a ``@decorator``.

    OpenTelemetry's ``start_as_current_span`` returns an object that is both, but
    its declared type advertises only the context-manager half. This models both
    so ``action`` type-checks in either form.
    """

    def __call__(self, func: _F) -> _F: ...


def current_recording_span() -> Span | None:
    span = trace.get_current_span()
    return span if span.is_recording() else None


def action(name: str) -> SpanScope:
    """Wrap a business operation in a named span.

    ``start_as_current_span`` is itself both a decorator and a context manager,
    and records uncaught exceptions / marks the span errored automatically. When
    no SDK provider is installed it yields a non-recording span, so this is a
    safe no-op. Invalid names fall back to a generic name rather than dropping
    the span.
    """
    if not valid_action_name(name):
        reject(f"invalid action name {name!r}")
        name = FALLBACK_ACTION
    return trace.get_tracer(TRACER_NAME).start_as_current_span(name)  # type: ignore[return-value]


def fields(**values: object) -> None:
    """Attach allowlisted, ``flowform.``-prefixed attributes to the current span."""
    span = current_recording_span()
    if span is not None:
        span.set_attributes(dict(filter_fields(values)))


def event(name: str, **values: object) -> None:
    """Record a bounded event with allowlisted attributes on the current span."""
    span = current_recording_span()
    if span is None:
        return
    if not valid_event_name(name):
        reject(f"invalid event name {name!r}")
        return
    span.add_event(name, attributes=dict(filter_fields(values)))
