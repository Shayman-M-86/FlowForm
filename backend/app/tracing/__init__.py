"""FlowForm tracing: OpenTelemetry bootstrap plus a safe business-span API.

Two concerns live here, each split into focused modules.

Business API (what application code imports)::

    from app import tracing

    @tracing.action("submission.answer.save")
    def save_answer(...):
        tracing.fields(outcome="accepted", question_type="single_choice")
        tracing.event("flowform.submission.done", outcome="accepted")

Public modules
--------------

api        action / fields / event / current_recording_span — the safe,
           allowlist-filtered business-span surface. No-ops when tracing is off.
extension  configure_tracing — Flask + library instrumentation entry point
           called by the application factory.
provider   initialize_tracing_provider / shutdown_tracing — fork-safe tracer
           provider and exporter lifecycle (Gunicorn post_fork / worker_exit).
policy     attribute normalization + allowlist filtering for exported values.
           Violations are dropped and logged, never raised — telemetry must
           not break a live request.
vocabulary value types, action/event name rules, and local constants
           (tracer name, allowlist, value/name bounds).

Environment-driven settings (enable, endpoint, sampling, defer) live in
``TracingSettings`` in :mod:`app.core.config`, not here.
"""

from __future__ import annotations

from app.tracing.api import action, current_recording_span, event, fields
from app.tracing.extension import configure_tracing
from app.tracing.provider import initialize_tracing_provider, shutdown_tracing

__all__ = [
    "action",
    "configure_tracing",
    "current_recording_span",
    "event",
    "fields",
    "initialize_tracing_provider",
    "shutdown_tracing",
]
