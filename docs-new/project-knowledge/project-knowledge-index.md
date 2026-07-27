---
title: Project Knowledge
aliases: ["Project Knowledge"]
document_type: overview
status: draft
authority: canonical
verified_against_commit: null
tags: [meta]
related_code: []
related_docs: ["FlowForm documentation", "Development workspace"]
---

# Project Knowledge

Project Knowledge is the maintained explanation of FlowForm as it currently
exists. It combines product meaning with the software, data, security,
infrastructure, and operational boundaries that realize that meaning. Current
code, tests, schemas, configuration, CI, and infrastructure definitions remain
the source of truth.

## Responsibility model

The collection is organized by ownership rather than by document format.
Product knowledge explains user-visible concepts and rules. Frontend and
backend knowledge explain the application responsibilities that implement
those rules. Data and security knowledge own persistence, encryption,
identity, authorization, and trust boundaries. Infrastructure and operations
explain how the system is assembled, deployed, observed, and maintained.
Engineering practices define cross-cutting ways of working, while reference
material records exact facts that support those explanations.

These areas are not independent silos. A feature may begin with a product rule,
cross frontend and backend responsibilities, persist through the data model,
and depend on security and operational guarantees. Each fact still has one
primary home; related documents connect the full path without repeating the
same explanation at every layer.

## Evidence and maturity

Canonical authority is earned through implementation evidence. A verified page
records the commit it was checked against; a draft exposes incomplete review;
and a scaffold carries no claim beyond its declared boundary. Proposals,
investigations, and unresolved decisions belong in [[development-workspace-index|Development
workspace]] until implementation evidence supports durable knowledge here.

## Related documents

- [[docs-new-index|FlowForm documentation]]
- [[development-workspace-index|Development workspace]]
- [[engineering-practices-index|Engineering practices]]
- [[infrastructure-index|Infrastructure knowledge]]
