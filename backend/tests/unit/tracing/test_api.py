"""Public business-tracing API tests.

The API is intentionally safe when tracing is unavailable. These tests isolate
the public decorator/context-manager surface and the policy-filtered writes
without requiring a global OpenTelemetry SDK provider.
"""

from __future__ import annotations

from collections.abc import Callable

import app.tracing.api as api


class _FakeSpan:
    def __init__(self, *, recording: bool = True) -> None:
        self.recording = recording
        self.attributes: dict[str, object] = {}
        self.events: list[tuple[str, dict[str, object]]] = []

    def is_recording(self) -> bool:
        return self.recording

    def set_attributes(self, attributes: dict[str, object]) -> None:
        self.attributes.update(attributes)

    def add_event(self, name: str, attributes: dict[str, object]) -> None:
        self.events.append((name, attributes))


class _FakeScope:
    def __init__(self, span: _FakeSpan) -> None:
        self.span = span
        self.entered = False

    def __enter__(self) -> _FakeSpan:
        self.entered = True
        return self.span

    def __exit__(self, *_args: object) -> None:
        self.entered = False

    def __call__(self, func: Callable[..., object]) -> Callable[..., object]:
        def wrapped(*args: object, **kwargs: object) -> object:
            with self:
                return func(*args, **kwargs)

        return wrapped


class _FakeTracer:
    def __init__(self, scope: _FakeScope) -> None:
        self.scope = scope
        self.names: list[str] = []

    def start_as_current_span(self, name: str) -> _FakeScope:
        self.names.append(name)
        return self.scope


def test_action_is_usable_as_a_decorator_and_context_manager(monkeypatch) -> None:
    scope = _FakeScope(_FakeSpan())
    tracer = _FakeTracer(scope)
    monkeypatch.setattr(api.trace, "get_tracer", lambda _name: tracer)

    @api.action("submission.session.start")
    def start() -> str:
        return "started"

    assert start() == "started"
    assert tracer.names == ["submission.session.start"]

    with api.action("submission.session.complete"):
        assert scope.entered is True

    assert tracer.names == ["submission.session.start", "submission.session.complete"]
    assert scope.entered is False


def test_fields_and_events_write_only_allowlisted_prefixed_values(monkeypatch) -> None:
    span = _FakeSpan()
    monkeypatch.setattr(api, "current_recording_span", lambda: span)

    api.fields(outcome="accepted", user_id="must-not-export")
    api.event("flowform.submission.core_committed", outcome="accepted", email="must-not-export")

    assert span.attributes == {"flowform.outcome": "accepted"}
    assert span.events == [
        ("flowform.submission.core_committed", {"flowform.outcome": "accepted"})
    ]


def test_fields_and_events_are_noops_without_a_recording_span(monkeypatch) -> None:
    monkeypatch.setattr(api, "current_recording_span", lambda: None)

    api.fields(outcome="accepted")
    api.event("flowform.submission.core_committed", outcome="accepted")
