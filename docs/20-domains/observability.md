---
title: Observability
aliases:
  - "Observability"
document_type: domain
status: draft
authority: canonical
verified_against_commit: null
tags: [backend, infrastructure]
related_code:
  - "../../backend/app/logging/"
  - "../../backend/gunicorn.conf.py"
  - "../../backend/app/api/v1/system/health.py"
  - "../../backend/app/schema/orm/core/audit_log.py"
  - "../../infra/containers/runtime/compose/"
  - "../../infra/containers/runtime/services/alloy/"
  - "../../infra/containers/runtime/services/alloy-app/"
  - "../../infra/containers/strategies/aws/services/caddy/Caddyfile.proxy"
  - "../../infra/containers/strategies/rehearsal/services/caddy/Caddyfile.proxy"
related_docs:
  - "Runtime containers"
  - "Backend implementation"
  - "Distributed tracing"
---

# Observability

Defines the health, logging, and tracing signals currently emitted or transported by the
application runtime. It describes checked-in behavior, not proof that a live
environment has working retention, dashboards, alerts, or incident response.

## Purpose

The domain provides enough signals to diagnose startup, HTTP requests,
cross-store submission steps, dependency readiness, and selected failures. The
shared host runtime ships app/proxy logs to Grafana Cloud Loki and backend/Caddy
traces to Grafana Cloud Tempo.

## Responsibilities

- Configure console JSON or human-readable logging, optional owner-only (`0600`)
  rotating files, root severity, selected dependency logger levels, and
  handler-level redaction for recognised credential-bearing fields and strings.
- Attach a request ID to request logs and the `X-Request-ID` response header,
  with optional end-to-end duration. The backend adopts a validated inbound
  `X-Request-ID` from Caddy (else mints its own) so proxy and backend lines share
  one ID — see [[logging-schema|Logging schema]] for the canonical field set and
  the correlation flow.
- Emit debug timing checkpoints for session start and answer-save steps without
  making them application state.
- Expose liveness and readiness endpoints; readiness executes `SELECT 1` against
  both core and response databases.
- Provide structured audit-log helpers and a core `audit_logs` table shape.
- Rotate container JSON logs locally and use Grafana Alloy to collect Docker
  logs on both hosts plus the proxy host's systemd journal.
- Redact invitation-token path segments and the complete `Referer` header from
  Caddy runtime/error records before those records reach the container log.
- Forward app-host backend logs to the proxy-host Alloy gateway, then to Grafana
  Cloud Loki; parse backend JSON and label only selected low-cardinality fields.
- Create Caddy and backend request spans with W3C trace-context propagation,
  instrument backend HTTP, SQLAlchemy, AWS SDK, and outbound `requests` calls,
  and export sampled spans through the two Alloy agents to Grafana Cloud Tempo.
- Inject active OpenTelemetry trace and span IDs into backend JSON logs and
  retain the equivalent Caddy access-log fields for Loki-to-Tempo correlation.

## Non-responsibilities

- No metrics, profiling, SLOs, alert rules, or on-call workflow are implemented
  by the inspected application/runtime definitions.
- Health endpoints do not attest Auth0, KMS, Secrets Manager, SES, proxy, or
  frontend availability.
- Request timing logs are diagnostic checkpoints, not durable performance
  measurements.
- A logging helper or audit table does not establish complete audit coverage,
  immutability policy, retention, access review, or compliance.

## Main signals and invariants

| Signal | Producer | Current contract |
| --- | --- | --- |
| Application log | Python logging | Timestamp, severity, logger, message, optional request/resource/timing fields; JSON in the shared runtime. |
| HTTP request log | Flask hooks | Request ID, method, matched route template or an unmatched sentinel, status, client address, and optional duration. |
| Timing checkpoint | Submission services | Debug-only elapsed and step-delta fields tied to the current request when present. |
| Liveness | `GET /api/v1/system/health` | Process-level timestamp and backend version response; no dependency check. |
| Readiness | `GET /api/v1/system/health/ready` | Timestamp and backend version; HTTP 200 only when both configured PostgreSQL sessions execute `SELECT 1`, otherwise 503. |
| Audit record | Logger helper or core row | Actor/action/resource metadata shape exists, but call-site coverage is not established. |
| Runtime log stream | Alloy/Loki | App/proxy container logs and proxy-host journal records; explicitly logs only. |
| Distributed trace | Caddy and backend OpenTelemetry instrumentation | Caddy ingress and backend Flask/dependency spans exported over OTLP; parent-based ratio sampling is configured by the backend. |
| Log/trace correlation | Backend formatter and Caddy access logs | Sampled request logs carry `trace_id` and `span_id`; request IDs remain available for log-only sources. |

Alloy keeps request IDs, route templates, status, and duration as parsed fields
rather than Loki labels to avoid high-cardinality streams. Backend, Caddy,
Squid, Alloy, and host journals use Docker rotation or the host journal as their
local source.

## Important workflows

1. Application startup first installs filtered bootstrap logging, validates
   settings and extensions, then replaces it with filtered application handlers.
2. When request logging is enabled, the before hook establishes request/timing
   context and the after hook emits the response record and ID header.
3. Submission orchestration emits timing checkpoints and explicit warning,
   error, or critical records for important partial failures and reconciliation.
4. Container health invokes the backend readiness endpoint; Docker uses its
   status to report backend health. Both health responses report the version
   loaded into application settings from `backend/pyproject.toml` at startup.
5. App-host Alloy reads Docker logs, parses backend JSON records, and forwards
   them over the private network to the proxy Alloy gateway.
6. Proxy Alloy combines those records with proxy-container and proxy-host
   journal logs and sends them to Grafana Cloud Loki with configured basic-auth
   credentials.
7. The backend exports OTLP/gRPC to app Alloy on `alloy:4317`; app Alloy relays
   to the proxy private address on `:4317`; proxy Alloy exports OTLP/HTTP to
   Grafana Cloud. Caddy exports directly to its local proxy Alloy receiver.

## Implementation map

- `backend/app/logging/logging_config.py` defines handlers, formatters, and
  startup configuration; `sensitive_data.py` filters emitted records;
  `request_logging.py` and `request_timing.py` own request-scoped signals;
  `tracing.py` owns OpenTelemetry instrumentation and export.
- `backend/app/api/v1/system/health.py` owns liveness and database readiness.
- `backend/app/logging/audit_logging.py`, `services/audit_log.py`, and
  `schema/orm/core/audit_log.py` define two audit-emission primitives.
- `infra/containers/runtime/compose/app.yml` and `proxy.yml` define health,
  rotation, Alloy privileges, and the private gateway.
- `infra/containers/runtime/services/alloy*/config.alloy` define collection,
  parsing, labelling, and Loki forwarding.
- Focused unit tests cover formatter/request-hook behavior; database integration
  tests cover audit-row constraints.

## Verified gaps and open questions

- No application call sites were found for either audit helper, so the presence
  of `audit_logs` does not currently provide action coverage.
- No metrics, alert definitions, checked-in dashboards, log/trace-retention
  policy, or tested notification path were found in the inspected boundary.
- Matched request logs use Flask route templates instead of caller-provided path
  values, and unmatched requests use a fixed sentinel. Handler filters also mask
  recognised secret fields and string patterns. These controls do not make an
  arbitrary unlabelled value safe to log; call sites must still exclude secrets.
- Caddy runtime/error records are outside the Python application filter. Their
  logger now removes invitation-token path segments and the complete `Referer`
  header, while Caddy handles Authorization and Cookie redaction. The URI rule
  is deliberately path-specific, and no secondary Alloy masking stage is
  configured for other caller-controlled proxy fields.
- Alloy deployment labels are hard-coded as `rehearsal` and `proxmox` in the
  checked-in configs even though the shared Compose files describe staging/prod
  reuse. Environment-label ownership needs clarification.
- The app Compose mounts systemd-journal paths into Alloy, but the app Alloy
  configuration has no journal source, so app-host journal collection is not
  currently active.
- Grafana credentials and destination parameters are wired through runtime
  configuration, but successful delivery, tenant retention, access controls, and
  production deployment were not verified.
- Squid observes HTTPS CONNECT tunnels and cannot participate in the application
  trace context. Its access logs remain correlated by request/network timing
  rather than an exact `trace_id`.
- Readiness checks only PostgreSQL. The desired behavior during Auth0, AWS key
  service, email, or log-sink outages is not defined.

## Related documents

- [[runtime-containers|Runtime containers]]
- [[backend|Backend implementation]]
- [[tracing|Distributed tracing]]
