---
title: External platform boundaries
aliases: ["External platform boundaries"]
document_type: architecture
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-08-04
tags: [infrastructure, configuration, security]
related_code: []
change_triggers:
  - "../../../infra/deployment/"
  - "../../../infra/contracts/"
  - "../../../.github/workflows/"
related_docs:
  - "Infrastructure knowledge"
  - "Deployment architecture"
  - "Configuration and secrets"
  - "Trust boundaries"
  - "Deployment design forces"
---

# External platform boundaries

FlowForm infrastructure depends on systems that are not wholly created or
governed by the deployment code. Those boundaries include identity, domain
registration and naming, email delivery approval, source-control protections,
cloud-account bootstrap, and secret values supplied after resources exist.

## Ownership classes

External dependencies fall into four durable classes:

| Class | FlowForm responsibility |
| --- | --- |
| Declared infrastructure | Create, update, and remove through reviewed deployment changes. |
| Imported foundation | Reference stable externally owned resources without assuming FlowForm can recreate their wider lifecycle. |
| Configured external service | Maintain the FlowForm-facing contract while the provider retains its own control plane and availability. |
| Human-authorized capability | Record prerequisites and evidence for approvals or protections that automation cannot safely infer. |

A dependency can move between classes through an explicit migration. Moving it
into infrastructure code also transfers ownership of import, replacement,
rollback, and deletion behaviour; it is not merely a convenience refactor.

## Bootstrap and steady state

Bootstrap authority is usually broader than runtime authority. Account setup,
external service configuration, initial secret seeding, and deployment-role
establishment should be separated from routine application operation.

```text
human or account bootstrap
          |
          v
deployment identity --> declared infrastructure
          |                    |
          v                    v
external contracts      runtime identities
          \                    /
           +--> running environment
```

Steady-state workloads should receive only the authority needed for their role.
Deployment automation should use short-lived identity and should not turn
bootstrap credentials into runtime configuration.

## Drift and verification

Repository validation cannot prove the state of an external tenant, registrar,
approval, branch protection, or account policy. Operational verification should
confirm that the external contract still exists, is scoped to the intended
environment, and can be recovered without relying on undocumented personal
state.

When a dependency is manual by design, document its owner, consequence of loss,
and evidence needed to re-establish it. Exact console steps and identifiers
belong with the owning runbook rather than this architecture page.

## Related documents

- [[infrastructure-index|Infrastructure knowledge]]
- [[deployment-index|Deployment architecture]]
- [[configuration|Configuration and secrets]]
- [[trust-boundaries|Trust boundaries]]
- [[design-forces-and-evolution|Deployment design forces]]
