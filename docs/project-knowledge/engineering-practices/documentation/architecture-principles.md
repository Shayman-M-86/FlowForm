---
title: Architecture principles
aliases: ["Architecture principles"]
document_type: overview
status: draft
authority: canonical
verified_evidence_digest: null
tags: [backend, frontend, infrastructure, security]
related_code:
  - "../../../../backend/app/"
  - "../../../../backend/openapi.yaml"
  - "../../../../frontend/apps/"
  - "../../../../frontend/packages/"
  - "../../../../frontend/scripts/generate-types.mjs"
  - "../../../../infra/deployment/aws/cdk/"
  - "../../../../infra/database/init/schema/"
related_docs: ["Engineering practices", "Documentation practice", "Project Knowledge", "Component map", "Security model"]
---

# Architecture principles

This page retains cross-cutting architectural patterns observed in FlowForm. It
is an engineering-practice aid for assessing changes, not an accepted decision
record or a substitute for ownership documentation. These observations require
implementation evidence before promotion from draft.

## How to use these observations

Use the patterns to locate the appropriate implementation owner and avoid
mistaking generated output or a deployment detail for an authoritative source.
An observed pattern is not a guarantee that every module follows it, nor does it
provide the rationale, alternatives, or exception policy of a decision record.

```text
product behaviour
       |
       v
application boundary --> domain/service policy --> persistence boundary
       |                         |
       v                         v
public contract            data constraints
       |
       v
generated consumers

deployment and operations surround these layers; they do not redefine them.
```

## Observed patterns retained from legacy material

- The backend separates HTTP routes and schemas from orchestration, domain
  rules, repositories, ORM models, and session management. Frontend deployable
  applications are separated from shared workspace packages.
- Backend schemas supply the checked-in OpenAPI contract; repository tooling
  derives frontend types and other contract artifacts. Generated artifacts are
  outputs, not independent contract sources.
- Application rules and database constraints both contribute to invariants;
  detailed lifecycle and persistence rules remain domain-owned.
- Survey editing and response collection use version-bound data. Verify the
  exact lifecycle in its owning domain before relying on this observation.
- Core and response storage have distinct responsibilities. Legacy material
  described opaque application-derived locators between them rather than
  cross-database foreign keys; this is not a complete security claim.
- CDK stacks and typed environment configuration describe cloud resources and
  runtime configuration. Differing local/cloud paths do not imply parity.

## Boundaries and follow-up

Detailed component, data, security, and deployment claims belong with their
owners. If any pattern should constrain future work, capture rationale,
alternatives, consequences, and exceptions in an accepted decision.

## Related documents

- [[engineering-practices-index|Engineering practices]]
- [[documentation-index|Documentation practice]]
- [[project-knowledge-index|Project Knowledge]]
- [[component-map|Component map]]
- [[security-model|Security model]]
