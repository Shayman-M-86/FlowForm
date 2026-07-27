---
title: Engineering practices
aliases: ["Engineering practices"]
document_type: overview
status: draft
authority: canonical
verified_against_commit: null
tags: [tooling]
related_code: []
related_docs: ["Project Knowledge", "Documentation practice"]
---

# Engineering practices

Engineering practices are the shared methods used to change FlowForm safely
and keep its implementation understandable. They cover evidence-driven
documentation, development and testing workflow, continuous integration,
repository conventions, and other practices that apply across more than one
product or infrastructure subsystem.

## Role in the system

Subsystem documentation explains what a component owns and how it behaves.
Engineering-practice documentation explains the repeatable methods used when
working across those components: how a change is validated, how generated
artifacts are handled, how evidence is recorded, and how temporary work is
kept separate from accepted knowledge.

A practice belongs here when several ownership branches depend on it. A rule
specific to one backend module, frontend application, deployment platform, or
operational service stays with that subject instead of becoming a global
convention.

## Documentation as an engineering practice

[[documentation-index|Documentation practice]] currently defines the
two-collection knowledge model, the evidence-based authoring process, and the
boundary between structural automation and human content review. Testing, CI,
and local-development practices will join this branch only when their legacy
material is migrated and verified.

## Related documents

- [[project-knowledge-index|Project Knowledge]]
- [[documentation-index|Documentation practice]]
