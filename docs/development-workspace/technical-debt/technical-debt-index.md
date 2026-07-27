---
title: Technical debt workspace
aliases: ["Technical debt workspace"]
document_type: planning-index
status: draft
authority: working
verified_evidence_digest: null
tags: [tooling]
related_code: []
related_docs: ["Development workspace"]
---

# Technical debt workspace

Technical debt workspace tracks known liabilities in implementation,
documentation, tooling, tests, maintainability, or operational practice that
need disposition. A debt item should make the impact, evidence, scope, and
uncertainty clear without overstating an unverified risk.

## Boundary

Debt is not a catch-all backlog. Use an investigation when the underlying
problem remains unclear, an idea for an uncommitted possibility, and planning
for the agreed remediation work. A debt record does not establish a current
architectural rule or guarantee that remediation has been scheduled.

## Lifecycle

Each item should be resolved, explicitly accepted, converted into a plan or
migration, or closed as invalid after investigation. Keep the disposition and
evidence current; archive resolved or superseded records when they no longer
need active tracking. Update Project Knowledge separately when the resolution
changes maintained system understanding.

```text
observed liability
       |
       v
 evidence + impact + ownership
       |
       +--> accept explicitly
       +--> investigate further
       +--> remediation plan --> implementation --> verify --> close
       +--> invalid / superseded -----------------------------> archive
```

## Related documents

- [[development-workspace-index|Development workspace]]
- [[ideas-index|Engineering ideas]]
- [[investigations-index|Engineering investigations]]
- [[planning-index|Engineering planning]]
- [[migrations-index|Engineering migrations]]
