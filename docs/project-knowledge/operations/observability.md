---
title: Observability
aliases: ["Observability"]
document_type: domain
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-27
tags: [backend, infrastructure]
related_code:
  - "../../../backend/app/logging/"
  - "../../../backend/app/tracing/"
  - "../../../backend/app/api/v1/system/health.py"
  - "../../../infra/containers/"
related_docs: ["Operations knowledge", "Distributed tracing", "Business tracing"]
---

# Observability

FlowForm's checked-in runtime emits structured application logs, request
correlation data, health responses, and OpenTelemetry traces. Container assets
also configure Alloy collection and forwarding. These are useful operational
signals, not evidence that a deployed environment has working dashboards,
alerts, retention, or a tested on-call response.

```text
request
  |
  +--> request ID ----------+
  +--> structured logs -----+--> Alloy / configured transport --> log backend
  +--> trace + spans -------+--> Alloy / configured transport --> trace backend
  +--> liveness/readiness -------------------------------> health consumer

correlation connects signals; it does not prove delivery or retention.
```

## Signal model

The logging package owns application formatting, filtering, request context,
and sensitive-value handling. Request processing can carry a request ID through
logs and response headers, while health endpoints distinguish process liveness
from readiness checks. The tracing package instruments backend work and can add
business spans; runtime container assets provide the log and trace transport
shape.

The readiness boundary is narrower than overall service health: database checks
can establish datastore reachability, but do not certify external identity,
email, KMS, secrets, frontend, or telemetry availability. Likewise, an audit
table or helper is a data shape and emission facility, not proof of complete
audit coverage or retention policy.

## Operational limits

Signals must avoid treating user-controlled or sensitive content as harmless
telemetry. Logs and trace attributes have different controls, and correlation
does not itself provide data redaction. Runtime configuration still needs
environment-specific confirmation for delivery credentials, tenant access,
sampling, retention, and labels.

## Related documents

- [[operations-index|Operations knowledge]]
- [[tracing-index|Distributed tracing]]
- [[business-tracing|Business tracing]]
