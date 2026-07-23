---
title: Logging schema
aliases:
  - "Logging schema"
  - "Canonical log schema"
document_type: reference
status: draft
authority: canonical
verified_against_commit: null
tags: [backend, infrastructure]
related_code:
  - "../../backend/app/logging/logging_config.py"
  - "../../backend/app/logging/request_logging.py"
  - "../../backend/app/utils/general.py"
  - "../../infra/containers/runtime/services/alloy/config.alloy"
  - "../../infra/containers/runtime/services/alloy-app/config.alloy"
  - "../../infra/containers/runtime/services/squid/squid.conf"
  - "../../infra/containers/strategies/aws/services/caddy/Caddyfile.proxy"
  - "../../infra/containers/strategies/rehearsal/services/caddy/Caddyfile.proxy"
related_docs:
  - "Observability"
  - "Runtime containers"
  - "Distributed tracing"
---

# Logging schema

Reference for the **canonical log schema** shared across every FlowForm log
emitter, and the two-agent Grafana Alloy pipeline that normalises them into it.
This is the field-level companion to the [[observability|Observability]] domain
doc: read that for the health/audit signals and the delivery path; read this for
what a log line looks like and why.

## Goal: one shape for every service

FlowForm ships logs from five emitters through two Alloy agents into one Grafana
Cloud Loki tenant. Each emitter's native wire format differs — backend JSON,
Caddy JSON, Squid token lines, Alloy logfmt, plain systemd-journal text — so the
pipeline maps them all onto a **single canonical schema**. Two properties matter:

1. **Uniform labels and field names.** `level` is lowercase everywhere, so
   `{level="error"}` matches the whole fleet instead of silently missing the
   services that emit `ERROR`. `status`, `path`, `client_ip`, `duration_ms`, and
   `request_id` mean the same thing and carry the same name regardless of which
   service produced the line.
2. **No duplication in the rendered line.** The timestamp lives in Loki's own
   timestamp column and `level` is an indexed label, so neither is repeated in
   the visible line body. Every other field is rendered as queryable logfmt
   (`key=value`) so `| logfmt` parses it at query time.

The result: every service's line body is canonical logfmt, and a human `msg`
field is folded in only where a service has genuine prose that the structured
fields don't already carry (startup banners, business events, errors).

## Canonical schema

### Labels (indexed, low-cardinality)

Labels are kept deliberately small — every distinct label-value combination is a
separate Loki stream, so high-cardinality values (paths with UUIDs, per-request
IDs) must **never** be labels.

| Label | Source | Notes |
| --- | --- | --- |
| `service_name` / `service` | compose service name | e.g. `backend`, `caddy`, `squid`, `alloy` |
| `level` | normalised **lowercase** | `debug` / `info` / `warning` / `error` / `critical` |
| `environment` | static Alloy relabel | `rehearsal` on the Proxmox boxes today |
| `platform` | static Alloy relabel | `proxmox` today |
| `host_role` | static Alloy relabel | `app` or `proxy` |
| `method` | HTTP method | backend / caddy / squid request lines only |

### Parsed fields (queryable via `| logfmt`, NOT labels)

| Field | Meaning |
| --- | --- |
| `status` | HTTP status code |
| `path` | request path (route template on the backend; raw URI on caddy/squid) |
| `client_ip` | client address |
| `duration_ms` | request duration in **milliseconds** |
| `request_id` | per-request correlation ID (see below) |
| `trace_id` | 32-character OpenTelemetry trace ID when an active sampled span exists |
| `span_id` | 16-character OpenTelemetry span ID when an active sampled span exists |
| `logger` | emitting logger name |
| `event_type` | e.g. `app_startup` |
| `user_id` | when available |
| `msg` | human message, only on lines that have real prose |

Service-specific extras also appear as fields: squid `cache_result`, `bytes`,
`hier`, `mime`; caddy `upstream`, `err_id`.

## Per-service normalisation

Each source emits the richest canonical-shaped format it can, and a thin Alloy
stage maps it the rest of the way. Three of the four are handled differently
because of what each tool can and cannot emit.

### Backend — source-normalised JSON

`JsonFormatter` in
[logging_config.py](../../backend/app/logging/logging_config.py) emits one JSON
object per record with canonical keys directly:

- `level` is emitted **lowercase** (`record.levelname.lower()`).
- LogRecord attributes are renamed to canonical JSON keys on the way out:
  `status_code` → `status`, `remote_addr` → `client_ip`. `request_id`,
  `method`, `path`, `duration_ms`, `logger`, `event_type`, `user_id`,
  `environment` pass through under their own names.
- OpenTelemetry logging instrumentation injects `otelTraceID` and `otelSpanID`
  into active-span records; the formatter emits them as `trace_id` and
  `span_id`, omitting zero or unset values.
- `message` is the fully-interpolated human string.

The app-box Alloy ([alloy-app/config.alloy](../../infra/containers/runtime/services/alloy-app/config.alloy))
parses that JSON and **rebuilds the line as logfmt**, dropping `ts`/`level`. On
request lines (`method` present) the `msg` field is suppressed, because the
backend's request message is just prose restating `method`/`path`/`status`/
`duration` that the structured fields already carry. On non-request lines
(startup, business events, errors) `msg` is kept as the sole content.

### Squid — source-normalised logfmt

Squid cannot emit JSON. Its `logformat flowform_access` in
[squid.conf](../../infra/containers/runtime/services/squid/squid.conf) is
written as canonical logfmt `key=value` tokens
(`duration_ms=`, `client_ip=`, `status=`, `method=`, `path=`, …). The proxy
Alloy parses it with `stage.logfmt`.

### Caddy — Alloy-remapped JSON

Caddy's top-level JSON keys (`ts`, `msg`, `status`, `request>uri`, `duration`)
are fixed and can't be renamed in the Caddyfile, so the canonical names are
produced by **Alloy remapping**, not by Caddy. The proxy Alloy `stage.json`
maps `request.uri` → `path`, `request.client_ip` → `client_ip`,
`request.method` → `method`, and converts Caddy's `duration` (seconds) to
`duration_ms`. It also maps the tracing handler's `traceID` and `spanID` fields
to canonical `trace_id` and `span_id`, then rebuilds the line as logfmt.

Two Caddyfile facts are load-bearing:

- **Access logging requires a `log` directive inside the site block.** A `log`
  in the *global options* block only reconfigures Caddy's runtime logger
  (health-checker, TLS, admin) and produces **zero** request lines. The `log`
  block lives in the `{$API_DOMAIN}` site block for this reason.
- **The redaction filter is security-critical and must be preserved.** It
  redacts the invitation token in the request URI
  (`/api/v1/account/invitations/resolve/<token>` → `[REDACTED]`) and replaces the
  `Referer` header, before the line is ever written.

### Alloy — its own logs

Both agents also emit their own logs into their pipelines. A `stage.match`
scoped to `{service_name="alloy"} |= "msg="` parses the logfmt fields, labels a
lowercase `level`, and rebuilds the line as logfmt without `ts`/`level` — so
Alloy's self-logs follow the same schema and always carry a `level` label.

### systemd-journal — known gap

Proxy-host journal lines are freeform and mostly carry no severity token. They
fall back to Grafana's `detected_level`; there is no promise of a `level` label
on every journal line.

## Request-ID correlation (Caddy ↔ backend)

Caddy and the backend now share **one** request ID so a proxy line can be joined
to its backend line in Loki.

1. Each Caddyfile generates `{http.request.uuid}` — one stable UUID per request —
   and uses the same value in two places:
   - `log_append request_id {http.request.uuid}` records it as a top-level
     `request_id` in Caddy's access-log JSON (mapped into the schema by the proxy
     Alloy).
   - `header_up X-Request-ID {http.request.uuid}` forwards it upstream to the
     backend (proxy-aware header manipulation).
2. The backend's `before_request` hook
   ([request_logging.py](../../backend/app/logging/request_logging.py)) **adopts a
   valid inbound `X-Request-ID`** and otherwise mints its own `uuid4()`.

Because the header is client-influenced, adoption is defensive:

- The value is length-guarded (max 45 chars) **before** parsing, then validated
  as a UUID (`uuid.UUID`, catching both `ValueError` and `TypeError`).
- Accepted IDs are re-rendered to canonical string form, so what is logged and
  echoed back in the `X-Request-ID` response header is always our own rendering,
  never the caller's raw bytes.
- A rejected header logs a WARNING (so a misbehaving upstream is visible) with the
  value passed only through a length-bounded `repr()`, which escapes control
  characters — a newline can't forge a second log line.
- A bad header never raises into the request; it falls back to a fresh UUID.

## Trace correlation

For sampled requests, Caddy and backend logs carry canonical `trace_id` and
`span_id` fields. The W3C trace context propagated from Caddy into the backend
keeps their spans in one trace. Query Loki with `| logfmt | trace_id="<id>"`,
then open that trace in the configured Tempo data source. `request_id` remains
the fallback correlation key for unsampled requests and for Squid, whose HTTPS
CONNECT view does not expose application trace context.

## Level mapping

`get_log_level` in [general.py](../../backend/app/utils/general.py) maps HTTP
status to severity for request logs:

| Status | Level |
| --- | --- |
| 2xx / 3xx | `info` |
| 4xx | `warning` |
| 5xx | `error` |

2xx/3xx log at **INFO** (not DEBUG) so completed requests surface at the default
INFO root level in every environment. This matters under gunicorn (prod /
rehearsal): unlike the Flask dev server it emits no werkzeug access line, so with
2xx at DEBUG a successful request produced no log at all.

## Startup logging

On startup the backend emits two INFO records via `log_startup`
([logging_config.py](../../backend/app/logging/logging_config.py)): a success
banner (version, listen address, debug flag; `event_type=app_startup`) and an
environment record (`Running in <env> environment`, carrying
`environment=<dev|test|prod>`). The Flask dev reloader's parent process is
skipped (it sets `WERKZEUG_RUN_MAIN` unset-to-non-`true`); gunicorn, which sets
no such marker, emits normally.

## Validation

- **Alloy config:** run the pinned `grafana/alloy:v1.5.1` image briefly with
  each configuration and placeholder environment values. A successful graph
  evaluation and receiver startup prove the checked-in component syntax.
- **Caddyfile:** `caddy adapt --config <Caddyfile>` (via the `caddy:latest`
  image, passing `API_DOMAIN`/`APP_PRIVATE_IP` env). The AWS copy reports a
  `dns.providers.route53` "module not registered" error under the stock image —
  that plugin is baked into the real deployment and the error is expected here.
- **Backend:** `bash backend/scripts/run-tests.sh --ai -k logging`.

## Related documents

- [[observability|Observability]]
- [[runtime-containers|Runtime containers]]
- [[tracing|Distributed tracing]]
