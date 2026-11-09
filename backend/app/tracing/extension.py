"""Flask and third-party library instrumentation setup.

``configure_tracing`` is the single entry point the application factory calls to
turn tracing on. It instruments Flask and the outbound-library clients, then
creates the exporter provider unless creation is deferred to post-fork (see
:mod:`app.tracing.provider`). Library instrumentation is global and installed at
most once per process.
"""

from __future__ import annotations

import re
from typing import Any

from flask import Flask
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.trace import Span

from app.core.config import Settings
from app.tracing.provider import DEFERRED_EXTENSION, initialize_tracing_provider

_INSTRUMENTED_EXTENSION = "tracing_instrumented"
_HEALTH_TRACE_EXCLUDED_URLS = r"/api/v1/system/health(?:/ready)?(?:\?.*)?$"
_libraries_instrumented = False

# Cloudflare request headers. The origin is reachable only through the tunnel,
# so they come from Cloudflare; values are still validated before recording.
_CF_RAY = re.compile(r"^[0-9a-f]{16}-(?P<colo>[A-Z]{3})$")
_COUNTRY = re.compile(r"^[A-Z]{2}$")
_REGION = re.compile(r"^[A-Z0-9]{1,3}$")


def _record_edge_route(span: Span, environ: dict[str, Any]) -> None:
    """Record coarse client origin and Cloudflare edge on the server span.

    Records the edge data centre (from CF-Ray), the client's IP version and
    country/region, never the client address itself, so routing can be
    analysed without the edge's own trace.
    """
    if not span.is_recording():
        return
    ray = _CF_RAY.match(environ.get("HTTP_CF_RAY", ""))
    if ray:
        span.set_attribute("cloudflare.colo", ray["colo"])
    client_ip = environ.get("HTTP_CF_CONNECTING_IP", "")
    if client_ip:
        span.set_attribute("flowform.client.ip_version", "6" if ":" in client_ip else "4")
    country = environ.get("HTTP_CF_IPCOUNTRY", "").upper()
    if _COUNTRY.match(country) and country != "XX":
        span.set_attribute("geo.country.iso_code", country)
        region = environ.get("HTTP_CF_REGION_CODE", "").upper()
        if _REGION.match(region):
            span.set_attribute("geo.region.iso_code", f"{country}-{region}")


def _instrument_libraries() -> None:
    """Instrument outbound libraries once per process (global, not per-app)."""
    global _libraries_instrumented
    if _libraries_instrumented:
        return

    RequestsInstrumentor().instrument()
    BotocoreInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()
    LoggingInstrumentor().instrument(set_logging_format=False)
    _libraries_instrumented = True


def configure_tracing(app: Flask, settings: Settings) -> None:
    """Instrument the app and start export, unless disabled or deferred.

    When ``defer_provider`` is set (Gunicorn preload), instrumentation is
    installed here but provider creation is left to ``post_fork`` so the batch
    exporter's thread is born in each worker.
    """
    tracing = settings.flowform.tracing
    if not tracing.enabled:
        return

    FlaskInstrumentor().instrument_app(app, excluded_urls=_HEALTH_TRACE_EXCLUDED_URLS, request_hook=_record_edge_route)
    _instrument_libraries()
    app.extensions[_INSTRUMENTED_EXTENSION] = True

    if tracing.defer_provider:
        app.extensions[DEFERRED_EXTENSION] = True
    else:
        initialize_tracing_provider(app)
