---
title: Operations knowledge
aliases: ["Operations knowledge"]
document_type: overview
status: verified
authority: canonical
verified_evidence_digest: sha256:e74ecc9f33ef453b21f678c16a8bf805516fed59e48bdf3aab8853d9f0e9f697
last_edited: 2026-07-27
tags: [infrastructure]
related_code:
  - "../../../backend/app/logging/"
  - "../../../backend/app/tracing/"
  - "../../../infra/containers/"
related_docs: ["Observability", "Distributed tracing"]
---

# Operations knowledge

This branch owns the runtime signals and operational boundaries that help
operators understand FlowForm. It covers logs, health endpoints, traces, and
their configured collection paths. It does not certify a live Grafana tenant,
dashboard, alert, retention, or incident-response programme: those require
environment evidence beyond checked-in code and configuration.

Observability describes the application and runtime signals as one operational
model. The tracing branch narrows that model to propagation, transport,
correlation, and application-owned business spans.

```text
running application
   |       |       |
   v       v       v
 logs    health   traces
   |               |
   +------> collection/transport
                    |
                    v
          external operational systems
```

## Related documents

- [[observability|Observability]]
- [[tracing-index|Distributed tracing]]
