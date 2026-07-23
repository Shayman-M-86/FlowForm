from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest
from flask import Flask

import app.tracing.provider as provider
from app.core.config import Settings, TracingSettings
from app.core.errors import InitializationError


def _settings(*, enabled: bool) -> Settings:
    return cast(
        Settings,
        SimpleNamespace(
            flowform=SimpleNamespace(
                env="test",
                tracing=TracingSettings(enabled=enabled),
            )
        ),
    )


def test_initialize_provider_is_idempotent(monkeypatch) -> None:
    app = Flask(__name__)
    app.extensions["settings"] = _settings(enabled=True)
    existing = SimpleNamespace(shutdown=lambda: None)
    app.extensions["tracing_provider"] = existing
    monkeypatch.setattr(provider, "TracerProvider", lambda **_: (_ for _ in ()).throw(AssertionError))

    provider.initialize_tracing_provider(app)

    assert app.extensions["tracing_provider"] is existing


def test_initialize_provider_is_noop_when_disabled(monkeypatch) -> None:
    app = Flask(__name__)
    app.extensions["settings"] = _settings(enabled=False)
    monkeypatch.setattr(provider, "TracerProvider", lambda **_: (_ for _ in ()).throw(AssertionError))

    provider.initialize_tracing_provider(app)

    assert "tracing_provider" not in app.extensions


def test_require_deferred_raises_when_enabled_but_not_deferred(monkeypatch) -> None:
    app = Flask(__name__)
    app.extensions["settings"] = _settings(enabled=True)
    monkeypatch.setattr(provider, "TracerProvider", lambda **_: (_ for _ in ()).throw(AssertionError))

    with pytest.raises(InitializationError):
        provider.initialize_tracing_provider(app, require_deferred=True)


def test_require_deferred_is_exempt_when_tracing_disabled(monkeypatch) -> None:
    # Tracing off is a valid deployment, not a broken handshake — no raise.
    app = Flask(__name__)
    app.extensions["settings"] = _settings(enabled=False)
    monkeypatch.setattr(provider, "TracerProvider", lambda **_: (_ for _ in ()).throw(AssertionError))

    provider.initialize_tracing_provider(app, require_deferred=True)

    assert "tracing_provider" not in app.extensions


def test_require_deferred_proceeds_when_flag_set(monkeypatch) -> None:
    app = Flask(__name__)
    app.extensions["settings"] = _settings(enabled=True)
    app.extensions[provider.DEFERRED_EXTENSION] = True
    stub_provider = SimpleNamespace(add_span_processor=lambda _p: None)
    monkeypatch.setattr(provider, "TracerProvider", lambda **_: stub_provider)
    monkeypatch.setattr(provider, "BatchSpanProcessor", lambda _e: object())
    monkeypatch.setattr(provider, "OTLPSpanExporter", lambda **_: object())
    monkeypatch.setattr(provider.trace, "set_tracer_provider", lambda _p: None)

    provider.initialize_tracing_provider(app, require_deferred=True)

    assert app.extensions["tracing_provider"] is not None


def test_shutdown_tracing_flushes_provider() -> None:
    app = Flask(__name__)
    calls: list[str] = []
    app.extensions["tracing_provider"] = SimpleNamespace(shutdown=lambda: calls.append("shutdown"))

    provider.shutdown_tracing(app)

    assert calls == ["shutdown"]
    assert "tracing_provider" not in app.extensions
