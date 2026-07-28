---
title: Engineering planning
aliases: ["Engineering planning"]
document_type: planning-index
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-07-28
tags: [meta]
related_code: []
related_docs: ["Development workspace"]
---

# Engineering planning

Engineering planning coordinates intended work: its objective, scope,
sequencing, dependencies, risks, validation, and completion criteria. Plans
remain working documents even when detailed; they are not proof that work has
been carried out or that an approach is accepted architecture.

## Boundary

Use a decision document for a durable choice, an investigation for evidence,
and a migration document for a state transition with cutover concerns. A plan
may link to each, but should not duplicate their analysis. Do not use planning
to publish current operational instructions or canonical system behaviour.

## Lifecycle

Revise plans as constraints or evidence change. When implementation concludes,
record the outcome in the appropriate current-state documentation only after
verification; archive the plan if its active coordination role has ended.
Incomplete or cancelled plans remain useful when their status and blockers are
plainly stated.

```text
decision + evidence
        |
        v
objective --> scope --> sequence --> validation --> implementation
                                                      |
                                   +------------------+----------------+
                                   |                                   |
                              verified outcome                    incomplete work
                                   |                                   |
                          Project Knowledge                         revise / archive
```

## Active plans

- [[aws-stack-specifications|AWS stack specifications]] consolidates the
  implemented settings, environment differences, dependencies, deployment
  status, and remaining gaps for every AWS CDK stack.
- [[aws-cdk-staging-plan|AWS CDK staging plan]] sequences proposed staging
  delivery work.
- [[aws-database-roles-and-bootstrap|AWS database roles and bootstrap design]]
  records how the existing PostgreSQL identity and initialization assets can be
  adapted for retained RDS.
- [[aws-database-stack-configuration|AWS DatabaseStack staging configuration]]
  records the proposed RDS service settings, lifecycle, monitoring, and delivery
  gates.

## Related documents

- [[development-workspace-index|Development workspace]]
- [[decisions-index|Engineering decisions]]
- [[investigations-index|Engineering investigations]]
- [[migrations-index|Engineering migrations]]
- [[archive-index|Engineering archive]]
