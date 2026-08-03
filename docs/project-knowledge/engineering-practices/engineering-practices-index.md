---
title: Engineering practices
aliases: ["Engineering practices"]
document_type: overview
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-08-03
tags: [tooling]
related_code:
  - "../../../frontend/package.json"
change_triggers:
  - "../../../tools/"
  - "../../../.github/workflows/"
  - "../../../backend/scripts/"
  - "../../../infra/env/dev/"
related_docs:
  - "Project Knowledge"
  - "Documentation practice"
  - "Local development"
  - "Testing workflow"
  - "Continuous integration"
  - "CI/CD implementation"
---

# Engineering practices

Engineering practices are the shared methods used to change FlowForm safely
and keep its implementation understandable. They cover evidence-driven
documentation, development and testing workflow, continuous integration,
repository conventions, and other practices that apply across more than one
product or infrastructure subsystem.

```text
understand --> change --> focused checks --> broader validation --> review
     ^                                                        |
     |                                                        v
documentation context <--- record evidence <--- accepted outcome
```

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

## Practice areas

[[documentation-index|Documentation practice]] defines the collection model,
evidence-based authoring process, and boundary between structural automation
and human review.

[[local-development|Local development]] describes the workstation loop and its
stateful runtime boundary. [[testing|Testing workflow]] selects and interprets
checks for a change. [[continuous-integration|Continuous integration]] explains
the hosted validation graph, while [[ci-cd-implementation|CI/CD
implementation]] maps CI and delivery concepts to checked-in workflows and
scripts. These are complementary: local workflow produces developer evidence,
testing establishes component confidence, and CI applies selected repository
gates; delivery remains an operational concern with infrastructure ownership.

Pages remain draft until their practice descriptions and code linkage are
checked against staged implementation evidence.

## Related documents

- [[project-knowledge-index|Project Knowledge]]
- [[documentation-index|Documentation practice]]
- [[local-development|Local development]]
- [[testing|Testing workflow]]
- [[continuous-integration|Continuous integration]]
- [[ci-cd-implementation|CI/CD implementation]]
