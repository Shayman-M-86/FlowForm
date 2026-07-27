---
title: Engineering decisions
aliases: ["Engineering decisions"]
document_type: decision-index
status: draft
authority: working
verified_evidence_digest: null
tags: [meta]
related_code: []
related_docs: ["Development workspace"]
---

# Engineering decisions

Engineering decisions record a choice, the context and alternatives considered,
and its current status. They make the decision boundary visible while a choice
is proposed, accepted, superseded, or rejected.

## Boundary

A decision is not an implementation plan, experimental result, or a restatement
of current system behaviour. Link supporting research, investigations, or
experiments; use planning documents for the execution work. Do not treat an
accepted decision alone as proof that its consequences have been implemented.

## Lifecycle

Keep the decision's status current as new evidence or later choices replace it.
When an accepted outcome has durable implementation-backed consequences,
distil those consequences into Project Knowledge. Superseded and rejected
decisions remain useful historical records and may later move to the archive.

```text
evidence + options + constraints
              |
              v
          proposed decision
          /       |       \
     accepted  rejected  superseded
         |         |         |
      planning     +---------+----> archive
         |
   implemented + verified
         |
         v
  Project Knowledge
```

## Current records

- [[0001-aws-staging-infrastructure-target|ADR 0001: AWS staging infrastructure target]]
  records the intended first staging topology and its exclusions.
- [[adr-template|ADR template]] is the working structure for a new record.

## Related documents

- [[development-workspace-index|Development workspace]]
- [[research-index|Engineering research]]
- [[investigations-index|Engineering investigations]]
- [[planning-index|Engineering planning]]
