---
title: Distributed tracing
aliases: ["Distributed tracing", "Tracing"]
document_type: reference
status: draft
authority: canonical
verified_against_commit: null
tags: [backend, infrastructure]
related_code:
  - "../../../../backend/app/tracing/"
  - "../../../../backend/app/logging/logging_config.py"
  - "../../../../infra/containers/"
related_docs: ["Operations knowledge", "Observability", "Business tracing"]
---

# Distributed tracing

This branch owns the repository-defined trace path: ingress context is
propagated to the backend, backend instrumentation and application spans emit
OpenTelemetry data, and container-side Alloy configuration relays that data to
the configured external endpoint. It also owns trace-to-log correlation rather
than the wider logging and health model.

Backend tracing configuration controls whether instrumentation/export is active,
the collector endpoint, sampling, and service identity. The logging formatter
can expose active trace and span identifiers, allowing an operator to pivot
between sampled traces and matching logs; a request ID remains useful when no
sampled trace exists. Provider lifecycle and exporter delivery depend on the
running process and external destination, so checked-in configuration does not
prove successful tenant delivery or retention.

The child page describes FlowForm's constrained business-span API. It adds
operation-level visibility without making arbitrary request values safe to
export.

## Related documents

- [[operations-index|Operations knowledge]]
- [[observability|Observability]]
- [[business-tracing|Business tracing]]
