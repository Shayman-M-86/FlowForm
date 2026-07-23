---
title: ADR template
aliases:
  - "ADR template"
document_type: decision-template
status: draft
authority: canonical
verified_against_commit: null
tags: [meta]
related_code: []
related_docs:
  - "Architecture decision records"
---

# ADR template
Provides the required structure for future FlowForm architecture decision records.

## Status
Use one of `proposed`, `accepted`, `superseded`, or `abandoned`. For a superseded decision, link the replacement ADR.

## Context
Describe the verified problem, relevant constraints, and forces that require a lasting choice. Separate observed current state from assumptions and proposals.

## Decision
State the selected option, its boundary, and when it takes effect. A proposed ADR records a candidate decision rather than current architecture.

## Consequences
Record positive, negative, migration, security, and operational consequences, including follow-up obligations that remain after acceptance.

## Alternatives considered
List only meaningful alternatives and the evidence-based reason each was not selected.

## References
Link the owning code, tests, configuration, relevant canonical documents, and any superseding or superseded ADRs. Record the implementation commit used as evidence when applicable.

## Related documents

- [[50-decisions/README|Architecture decision records]]
