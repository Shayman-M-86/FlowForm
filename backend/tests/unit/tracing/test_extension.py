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
    assert instrument_calls == [
        {"excluded_urls": extension._HEALTH_TRACE_EXCLUDED_URLS, "request_hook": extension._record_edge_route}
    ]


class _RecordingSpan:
    def __init__(self) -> None:
        self.attributes: dict[str, object] = {}

    def is_recording(self) -> bool:
        return True

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value


def test_edge_route_records_colo_ip_version_and_region_without_the_address() -> None:
    span = _RecordingSpan()
    extension._record_edge_route(
        cast(extension.Span, span),
        {
            "HTTP_CF_RAY": "a57d8b961b9a8249-SIN",
            "HTTP_CF_CONNECTING_IP": "2001:db8::1",
            "HTTP_CF_IPCOUNTRY": "AU",
            "HTTP_CF_REGION_CODE": "VIC",
        },
    )

    assert span.attributes == {
        "cloudflare.colo": "SIN",
        "flowform.client.ip_version": "6",
        "geo.country.iso_code": "AU",
        "geo.region.iso_code": "AU-VIC",
    }
    assert "2001:db8::1" not in span.attributes.values()


def test_edge_route_ignores_missing_and_malformed_headers() -> None:
    span = _RecordingSpan()
    extension._record_edge_route(
        cast(extension.Span, span),
        {"HTTP_CF_RAY": "not-a-ray", "HTTP_CF_IPCOUNTRY": "XX", "HTTP_CF_REGION_CODE": "VIC"},
    )

    assert span.attributes == {}
