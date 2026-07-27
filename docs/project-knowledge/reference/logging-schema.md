---
title: Logging schema
aliases: ["Logging schema", "Canonical log schema"]
document_type: reference
status: verified
authority: canonical
verified_evidence_digest: sha256:fb58492e81ff71c96b8cfb941d5edda8d7e6d9b6fe91a040510032f3072a7ab3
last_edited: 2026-07-27
tags: [backend, infrastructure]
related_code: ["../../../backend/app/logging/logging_config.py", "../../../backend/app/logging/request_logging.py", "../../../infra/containers/runtime/services/alloy/config.alloy", "../../../infra/containers/runtime/services/alloy-app/config.alloy", "../../../infra/containers/runtime/services/squid/squid.conf"]
related_docs: ["Observability", "Runtime containers", "Distributed tracing"]
---

# Logging schema

This page preserves the legacy canonical-log-schema reference. Backend, proxy,
and collector configuration are the authoritative sources; this draft does not
attest that every emitter or deployed pipeline currently conforms.

## Intended model

Legacy material describes several emitters flowing through Alloy agents to a
single Loki tenant. Native backend JSON, Caddy JSON, Squid token lines, Alloy
logfmt, and journal text are normalized into queryable logfmt. Keep indexed
labels low-cardinality: request IDs and unbounded paths belong in parsed fields,
not Loki labels.

```text
backend JSON ----+
Caddy JSON ------+
Squid tokens ----+--> Alloy parsing/normalization --> log transport --> Loki
journal text ----+              |
Alloy logfmt ----+              +--> low-cardinality labels
                                +--> request-specific parsed fields
```

| Class | Fields retained from the legacy schema |
| --- | --- |
| Labels | `service_name`/`service`, lowercase `level`, `environment`, `platform`, `host_role`, `method` |
| Parsed request fields | `status`, `path`, `client_ip`, `duration_ms`, `request_id` |
| Event/error fields | `msg`, error type/detail, and service-specific structured fields |

`request_id` is intended for correlation and `duration_ms` for request timing.
Confirm exact field names, redaction, labels, parse stages, and retention policy
in the linked backend and Alloy configuration before writing dashboards or
alerts. Do not log credentials, secret values, or other sensitive payloads.

## Related documents

- [[observability|Observability]]
- [[runtime-containers|Runtime containers]]
- [[tracing-index|Distributed tracing]]
