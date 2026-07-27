---
title: Business tracing
aliases: ["Business tracing", "Tracing API"]
document_type: implementation
status: draft
authority: canonical
verified_against_commit: null
tags: [backend]
related_code:
  - "../../../../backend/app/tracing/"
  - "../../../../backend/app/logging/logging_config.py"
  - "../../../../backend/app/logging/sensitive_data.py"
  - "../../../../backend/tests/unit/tracing/"
related_docs: ["Distributed tracing", "Observability"]
---

# Business tracing

The `backend/app/tracing/` package provides FlowForm-owned business spans on
top of OpenTelemetry instrumentation. Its purpose is to show a bounded business
operation and important checkpoints without spreading telemetry-provider calls
through services or exporting response, credential, or identity data.

The public surface has three roles: an action opens a named operation span,
fields describe stable properties of that span, and events record moments where
order or presence matters. Fields are for bounded dimensions an operator might
filter or aggregate; events are for transitions or checkpoints within the
operation. Underlying HTTP, database, and AWS instrumentation remains the
provider-level trace detail.

Trace attributes leave the process. The tracing policy therefore allows only
recognised, bounded, non-identifying keys and normalizes or drops unsuitable
values. High-cardinality identifiers, emails, credentials, and answer content
belong in neither action names nor trace attributes. Logging may hold
per-incident context under its own filtering policy, and matching trace IDs
provide the bridge between the two signal types.

## Related documents

- [[tracing-index|Distributed tracing]]
- [[observability|Observability]]
