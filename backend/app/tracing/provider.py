"""Tracer provider and span-exporter lifecycle.

The provider owns a ``BatchSpanProcessor`` whose background export thread must be
created *inside* each process that emits spans — never inherited across a fork.
Under Gunicorn (``defer_provider``) the provider is therefore created per worker
in ``post_fork`` rather than during preload. Provider handles are stashed on
``app.extensions`` so creation stays idempotent and shutdown can find them.
"""

from __future__ import annotations

from typing import Any

from flask import Flask
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

from app.core.config import Settings
from app.core.errors import InitializationError

_PROVIDER_EXTENSION = "tracing_provider"

# Set by configure_tracing when it instruments the app but leaves provider
# creation to post_fork. The Gunicorn hook passes require_deferred=True so a
# missing flag — meaning tracing was never configured, or was configured
# without deferral — fails loudly instead of silently skipping worker export.
DEFERRED_EXTENSION = "tracing_provider_deferred"


def initialize_tracing_provider(app: Flask, *, require_deferred: bool = False) -> None:
    """Create one tracer provider and exporter in the current process.

    Idempotent: a provider is created at most once per process. Safe to call
    from both ``configure_tracing`` (non-forking deployments) and Gunicorn's
    ``post_fork`` hook (one provider per worker).

    ``require_deferred`` makes the deferred-init handshake explicit: the caller
    (post_fork) asserts that ``configure_tracing`` ran during preload and marked
    the provider deferred. When tracing is enabled but the flag is missing, the
    boot contract changed out from under the fork hook, so raise rather than
    silently export nothing. Tracing being disabled is a valid config, not a
    contract breach, so it is exempt.
    """
    if app.extensions.get(_PROVIDER_EXTENSION) is not None:
        return

    settings: Settings = app.extensions["settings"]
    tracing = settings.flowform.tracing
    if not tracing.enabled:
        return

    if require_deferred and not app.extensions.get(DEFERRED_EXTENSION):
        raise InitializationError(
            "post_fork expected a deferred tracing provider, but configure_tracing "
            "did not defer one during preload. Tracing would not export from workers."
        )

    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": tracing.service_name,
                "deployment.environment": settings.flowform.env,
            }
        ),
        sampler=ParentBased(TraceIdRatioBased(tracing.sample_ratio)),
    )
    exporter = OTLPSpanExporter(
        endpoint=tracing.otlp_endpoint,
        insecure=tracing.otlp_endpoint.startswith("http://"),
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    app.extensions[_PROVIDER_EXTENSION] = provider


def shutdown_tracing(app: Flask) -> None:
    """Flush and stop the current process's tracer provider."""
    provider: Any = app.extensions.pop(_PROVIDER_EXTENSION, None)
    if provider is not None:
        provider.shutdown()
