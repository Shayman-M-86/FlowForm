---
title: Engineering planning
aliases: ["Engineering planning"]
document_type: planning-index
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-07-29
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

- [[three-level-ami-reorganization-checkpoint|Three-level AMI reorganization
  checkpoint]] records the paused, uncommitted infrastructure reorganization,
  its provisional ownership decisions, integration gaps, and safe resume
  boundary.
- [[aws-staging-runtime-convergence|AWS staging runtime convergence]] is the
  current execution plan. It tracks app-host access, backend startup, public
  TLS, recovery access, host replacement, and final runtime proof after the
  first Application deployment.
- [[aws-stack-specifications|AWS stack specifications]] consolidates the
  implemented settings, environment differences, dependencies, deployment
  status, and remaining gaps for every AWS CDK stack.
- [[aws-iam-database-auth-loose-threads|AWS IAM database authentication loose
  threads]] tracks the remaining runtime proof and deferred database cleanup.

## Completed design checkpoints

- [[aws-cdk-staging-plan|AWS CDK staging plan]] summarizes the infrastructure
  foundation already delivered and the later phases that remain.
- [[aws-database-roles-and-bootstrap|AWS database roles and bootstrap design]]
  records the implemented PostgreSQL identity and bootstrap boundaries.
- [[aws-database-stack-configuration|AWS DatabaseStack staging configuration]]
  records the deployed staging database decisions and intended production
  differences.

## Related documents

- [[development-workspace-index|Development workspace]]
- [[decisions-index|Engineering decisions]]
- [[investigations-index|Engineering investigations]]
- [[migrations-index|Engineering migrations]]
- [[archive-index|Engineering archive]]
