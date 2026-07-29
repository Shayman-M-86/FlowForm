---
title: Operations knowledge
aliases: ["Operations knowledge", "Observability", "Distributed tracing", "Business tracing"]
document_type: architecture
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-30
tags: [infrastructure, backend]
related_code:
  - "../../../backend/app/logging/logging_config.py"
  - "../../../backend/app/tracing/extension.py"
change_triggers:
  - "../../../backend/app/api/v1/system/health.py"
  - "../../../infra/containers/images/alloy/"
related_docs: ["Infrastructure knowledge", "Container runtime", "Proxmox rehearsal"]
---

# Operations knowledge

FlowForm emits structured application logs, health responses, request
correlation data, and OpenTelemetry traces. Runtime assets provide configured
collection and forwarding paths. These repository capabilities are signals for
operations, not proof of a live tenant, dashboard, alert, retention policy, or
incident response process.

```text
request
  +--> request ID and structured logs
  +--> liveness/readiness response
  `--> trace and application spans
                 |
                 v
          configured runtime transport
                 |
                 v
       external operational destination
```

## Signal boundaries

Logging owns formatting, filtering, request context, and sensitive-value
handling. Health endpoints distinguish process liveness from a narrower
readiness assessment. Tracing propagates context through backend work and can
add bounded FlowForm business spans alongside provider instrumentation.
Trace attributes are exported data: application-defined fields must remain
bounded and non-identifying, while credentials, answer content, and arbitrary
user values do not become safe merely because they aid diagnosis.

Correlation makes it possible to connect logs and sampled traces; it does not
guarantee either delivery or retention. Environment evidence is required to
establish destination access, sampling, labels, dashboards, and alerting.

## Related documents

- [[infrastructure-index|Infrastructure knowledge]]
- [[containers-index|Container runtime]]
- [[proxmox-index|Proxmox rehearsal]]
