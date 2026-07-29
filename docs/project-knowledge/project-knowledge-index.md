---
title: Project Knowledge
aliases: ["Project Knowledge"]
document_type: overview
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-30
tags: [meta]
related_code: []
change_triggers:
  - "../../backend/app/"
  - "../../frontend/apps/"
  - "../../frontend/packages/"
  - "../../infra/"
related_docs:
  - "FlowForm documentation"
  - "Development workspace"
  - "Product knowledge"
  - "Frontend implementation"
  - "Backend knowledge"
  - "Data knowledge"
  - "Security knowledge"
  - "Infrastructure knowledge"
  - "Operations knowledge"
  - "Engineering practices"
  - "Reference documentation"
---

# Project Knowledge

Project Knowledge is FlowForm's maintained explanation of the current system.
It describes what the platform does, which areas own each responsibility, and
how those areas meet at durable boundaries. The implementation remains the
source of truth.

FlowForm supports designing and publishing surveys, controlling access,
collecting responses, and reviewing results. Browser applications, backend
services, persistence, security controls, and deployment environments each own
part of that lifecycle.

## Ownership map

- [[product-index|Product knowledge]] owns user-visible concepts and rules.
- [[frontend-index|Frontend implementation]] and [[backend-index|Backend
  knowledge]] own browser and application-service responsibilities.
- [[data-index|Data knowledge]] and [[security-index|Security knowledge]] own
  persistence, protection, identity, and trust boundaries.
- [[infrastructure-index|Infrastructure knowledge]] and
  [[operations-index|Operations knowledge]] own runtime assembly, deployment,
  configuration, and operational signals.
- [[engineering-practices-index|Engineering practices]] owns shared ways of
  changing and validating the system.
- [[reference-index|Reference documentation]] points to stable repository facts
  and generated detail without duplicating implementation inventories.

A fact belongs in one of these areas even when a change crosses several. Use
links to connect the path rather than restating the same behaviour in each
branch.

## Maturity

Project Knowledge pages may be drafts while they are being corrected or
consolidated. Verification is deliberate and evidence-backed; it is not implied
by confident prose. Plans and unresolved choices remain in the
[[development-workspace-index|Development workspace]].

## Related documents

- [[docs-index|FlowForm documentation]]
- [[development-workspace-index|Development workspace]]
- [[product-index|Product knowledge]]
- [[frontend-index|Frontend implementation]]
- [[backend-index|Backend knowledge]]
- [[data-index|Data knowledge]]
- [[security-index|Security knowledge]]
- [[infrastructure-index|Infrastructure knowledge]]
- [[operations-index|Operations knowledge]]
- [[engineering-practices-index|Engineering practices]]
- [[reference-index|Reference documentation]]
