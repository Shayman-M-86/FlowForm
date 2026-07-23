"""Flask and third-party library instrumentation setup.

``configure_tracing`` is the single entry point the application factory calls to
turn tracing on. It instruments Flask and the outbound-library clients, then
creates the exporter provider unless creation is deferred to post-fork (see
:mod:`app.tracing.provider`). Library instrumentation is global and installed at
most once per process.
"""

from __future__ import annotations

from flask import Flask
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from app.core.config import Settings
from app.tracing.provider import DEFERRED_EXTENSION, initialize_tracing_provider

_INSTRUMENTED_EXTENSION = "tracing_instrumented"
_libraries_instrumented = False


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

    FlaskInstrumentor().instrument_app(app)
    _instrument_libraries()
    app.extensions[_INSTRUMENTED_EXTENSION] = True

    if tracing.defer_provider:
        app.extensions[DEFERRED_EXTENSION] = True
    else:
        initialize_tracing_provider(app)
