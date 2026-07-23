from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from flask import Flask

import app.tracing.extension as extension
from app.core.config import Settings, TracingSettings


def _settings(*, enabled: bool, defer_provider: bool = False) -> Settings:
    return cast(
        Settings,
        SimpleNamespace(
            flowform=SimpleNamespace(
                env="test",
                tracing=TracingSettings(enabled=enabled, defer_provider=defer_provider),
            )
        ),
    )


def test_configure_tracing_is_noop_when_disabled(monkeypatch) -> None:
    app = Flask(__name__)
    monkeypatch.setattr(extension, "_instrument_libraries", lambda: (_ for _ in ()).throw(AssertionError))

    extension.configure_tracing(app, _settings(enabled=False))

    assert "tracing_instrumented" not in app.extensions


def test_configure_tracing_defers_provider_when_requested(monkeypatch) -> None:
    app = Flask(__name__)
    instrument_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        extension.FlaskInstrumentor,
        "instrument_app",
        lambda *_a, **kwargs: instrument_calls.append(kwargs),
    )
    monkeypatch.setattr(extension, "_instrument_libraries", lambda: None)
    monkeypatch.setattr(
        extension,
        "initialize_tracing_provider",
        lambda _app: (_ for _ in ()).throw(AssertionError("provider must be deferred")),
    )

    extension.configure_tracing(app, _settings(enabled=True, defer_provider=True))

    assert app.extensions["tracing_instrumented"] is True
    assert instrument_calls == [{"excluded_urls": extension._HEALTH_TRACE_EXCLUDED_URLS}]
