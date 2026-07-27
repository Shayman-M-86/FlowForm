---
title: Distributed tracing
aliases:
  - "Distributed tracing"
  - "Tracing"
document_type: reference
status: draft
authority: canonical
verified_against_commit: null
tags: [backend, infrastructure]
related_code:
  - "../../backend/app/tracing/"
  - "../../backend/app/logging/logging_config.py"
  - "../../backend/gunicorn.conf.py"
  - "../../infra/containers/runtime/services/alloy-app/config.alloy"
  - "../../infra/containers/runtime/services/alloy/config.alloy"
  - "../../infra/containers/runtime/compose/app.yml"
  - "../../infra/containers/runtime/compose/proxy.yml"
  - "../../infra/containers/strategies/aws/services/caddy/Caddyfile.proxy"
  - "../../infra/containers/strategies/rehearsal/services/caddy/Caddyfile.proxy"
related_docs:
  - "Observability"
  - "Business tracing"
  - "Logging schema"
  - "Proxmox rehearsal observability"
---

# Distributed tracing

Reference for FlowForm's backend and Caddy spans, two-hop Alloy transport, and
log-to-trace correlation. It describes checked-in behavior, not proof of live
Grafana Cloud delivery or retention.

FlowForm's application-owned action spans, bounded attributes, and events are
documented separately in [[business-tracing|Business tracing]]. This reference
owns the transport, provider lifecycle, and trace/log correlation facts.

## Trace path

1. Caddy starts an ingress span and propagates W3C trace context upstream.
2. Flask continues that context. OpenTelemetry instrumentation creates spans
   for Flask, SQLAlchemy, Botocore, and outbound `requests` operations.
   FlowForm services and middleware can add business-action child spans to that
   active context through the bounded API described in [[business-tracing|Business
   tracing]].
   The liveness and readiness probe URLs are excluded from Flask tracing to
   avoid high-frequency operational noise.
3. The backend exports OTLP/gRPC to app Alloy at `http://alloy:4317`.
4. App Alloy batches and relays spans to `${PROXY_PRIVATE_IP}:4317`.
5. Caddy exports OTLP/HTTP to proxy Alloy at
   `http://alloy:4318/v1/traces`.
6. Proxy Alloy combines relayed backend spans with local Caddy spans and exports
   OTLP/gRPC with TLS to `GRAFANA_CLOUD_TEMPO_ENDPOINT` using the Tempo tenant
   ID and file-backed Cloud Access Policy token.

Caddy runs on the proxy Compose network and exports directly to its local
OTLP/HTTP receiver on `alloy:4318`; port `4317` remains the OTLP/gRPC gateway
for the app-host relay. Squid is intentionally outside the trace: an HTTPS
CONNECT proxy cannot observe or propagate the application HTTP trace context.

## Backend settings

| Variable | Default | Contract |
| --- | --- | --- |
| `FLOWFORM_TRACING_ENABLED` | `false` | Installs instrumentation and creates an exporter only when enabled. |
| `FLOWFORM_TRACING_OTLP_ENDPOINT` | `http://alloy:4317` | OTLP/gRPC collector endpoint. Plain HTTP selects insecure transport on the private Compose network. |
| `FLOWFORM_TRACING_SAMPLE_RATIO` | `1.0` | Ratio sampler value, validated from `0.0` through `1.0` and wrapped in parent-based sampling. |
| `FLOWFORM_TRACING_SERVICE_NAME` | `backend` | OpenTelemetry `service.name` resource attribute. |

The provider also sets `deployment.environment` from `FLOWFORM_ENV`.

## Gunicorn lifecycle

Gunicorn preloads the Flask application, so instrumentation wrappers are
installed before workers fork while the tracer provider, exporter, and batch
thread are deferred. `post_fork` creates one provider per worker after disposing
inherited database pools. `worker_exit` flushes and shuts down that provider.
Non-Gunicorn entry points initialize the provider during application creation.

## Log correlation

OpenTelemetry logging instrumentation injects the active span identifiers into
Python `LogRecord` objects without replacing FlowForm's formatter. Backend JSON
logs expose canonical `trace_id` and `span_id` fields only when the identifiers
are non-zero. Caddy access logs expose the same field names after Alloy maps
`traceID` and `spanID`.

Use `trace_id` for exact Loki-to-Tempo correlation on sampled requests.
`request_id` remains the cross-service fallback for unsampled requests and
log-only sources. The Grafana Tempo data-source name and UID are deployment
state rather than repository configuration and must be resolved in the target
Grafana stack before adding derived-field links or dashboards.

## Security and boundaries

- The Grafana Cloud token remains a file-backed Docker secret and is marked
  secret in Alloy. URLs and user/instance IDs are non-secret runtime parameters.
- Proxy OTLP port `4317` binds to `PROXY_PRIVATE_IP`, not a public interface.
- Trace attributes are telemetry and must not contain credentials or sensitive
  form answers. Logging redaction does not sanitize arbitrary span attributes.
- Successful config evaluation does not attest live tenant authentication,
  delivery, retention, or access control.

## Related documents

- [[observability|Observability]]
- [[business-tracing|Business tracing]]
- [[logging-schema|Logging schema]]
- [[proxmox-rehearsal-observability|Proxmox rehearsal observability]]
