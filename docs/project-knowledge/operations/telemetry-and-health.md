---
title: Telemetry and health
aliases: ["Telemetry and health", "Logging and tracing", "Distributed tracing"]
document_type: architecture
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-08-04
tags: [backend, infrastructure, security]
related_code:
  - "../../../backend/app/api/v1/system/health.py"
  - "../../../backend/app/logging/logging_config.py"
  - "../../../backend/app/logging/request_logging.py"
  - "../../../backend/app/logging/sensitive_data.py"
  - "../../../backend/app/tracing/api.py"
  - "../../../backend/app/tracing/policy.py"
  - "../../../infra/containers/images/alloy/config/app.alloy"
  - "../../../infra/containers/images/alloy/config/proxy.alloy"
change_triggers:
  - "../../../backend/app/logging/"
  - "../../../backend/app/tracing/"
  - "../../../backend/app/api/v1/system/"
  - "../../../infra/containers/images/alloy/"
  - "../../../infra/containers/images/caddy/"
related_docs:
  - "Operations knowledge"
  - "Container runtime"
  - "Security model"
  - "Data flows"
---

# Telemetry and health

FlowForm produces health responses, structured logs, request correlation data,
and OpenTelemetry traces. Runtime definitions provide collection and forwarding
paths for those signals. Checked-in producers and transports demonstrate
capability, not successful delivery, retention, dashboards, alerting, or an
incident-response process in a live environment.

## Health boundary

The system API exposes two unauthenticated probes:

| Probe | Meaning |
| --- | --- |
| `/api/v1/system/health` | Process liveness plus application version and current timestamp. It does not check external dependencies. |
| `/api/v1/system/health/ready` | Readiness based on `SELECT 1` against both core and response databases. Each worker caches success or failure for ten seconds. |

Readiness does not attest Auth0, AWS key or secret services, email delivery,
the proxy, either frontend, or the telemetry destination. It is intentionally a
narrow database-connectivity signal.

## Logging and request correlation

The backend can emit structured JSON with lowercase severity and stable fields
for request ID, route template, HTTP status, client address, duration in
milliseconds, audit context, and active trace identifiers. Sensitive-data
filters protect application-owned handlers, but call sites must still avoid
placing credentials, respondent answers, or arbitrary identifying values in
logs.

Caddy assigns a UUID request ID, records it in its access log, and forwards it
as `X-Request-ID`. The backend accepts only a UUID-shaped inbound value,
normalizes it, or creates a new UUID. This lets proxy and backend records be
joined without trusting caller-provided text. Matched backend requests log the
route template instead of a raw caller-controlled path.

```text
Caddy request UUID ------> Caddy access record
          |
          +-- X-Request-ID --> backend request record
                                      |
                               trace_id / span_id
```

Alloy parses and normalizes backend, Caddy, Squid, and agent logs. Values such
as request IDs, paths, status, and duration remain parsed fields rather than
high-cardinality Loki labels. Proxy logging also redacts invitation-token path
segments and the complete `Referer` value before collection.

## Distributed and business tracing

Caddy and Flask can participate in one W3C trace context. Backend
instrumentation covers Flask, SQLAlchemy, AWS SDK, and outbound HTTP work, while
the application adds selected business-action child spans through three
primitives:

| Primitive | Purpose |
| --- | --- |
| `action(name)` | Opens a named business span as a decorator or context manager. |
| `fields(**values)` | Adds searchable properties describing the current span. |
| `event(name, **values)` | Marks an ordered or time-relevant moment inside the current span. |

Trace fields cross an outbound telemetry boundary. The application therefore
allowlists field names, prefixes accepted attributes with `flowform.`, bounds
field counts and value sizes, and drops policy violations rather than allowing
telemetry to fail a request. Fields must be bounded and non-identifying; raw
record identifiers, credentials, email addresses, and survey answers do not
belong in traces.

The app-host Alloy receives backend OTLP traffic and relays it to the proxy-host
Alloy. The proxy collector combines backend and Caddy spans for export to the
configured destination. Squid observes HTTP proxy and HTTPS tunnel traffic but
does not participate in application trace context.

## Operational limits

- Request timing checkpoints are diagnostic signals, not durable performance measurements.
- Logging helpers and the audit-log schema do not establish complete audit coverage or an immutability and retention policy.
- The inspected application and runtime definitions do not establish metrics, profiling, SLOs, alert rules, checked-in dashboards, or an on-call workflow.
- Repository configuration cannot prove telemetry authentication, delivery, sampling results, retention, or access control in a live tenant.

## Related documents

- [[operations-index|Operations knowledge]]
- [[containers-index|Container runtime]]
- [[security-model|Security model]]
- [[data-flows|Data flows]]
