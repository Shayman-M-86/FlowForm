---
title: Architecture decision records
aliases:
  - "Architecture decision records"
document_type: decision-index
status: draft
authority: canonical
verified_against_commit: null
tags: [meta]
related_code: []
related_docs:
  - "ADR template"
  - "Planning workspace"
  - "Documentation model"
---

# Architecture decision records
Indexes lasting architectural decisions for FlowForm.

## Purpose
This directory stores records of durable architectural decisions after their context, choice, and consequences can be supported by repository evidence. It is an index and process boundary, not evidence that a decision has already been accepted.

## What belongs here
Use an ADR when a lasting choice needs its rationale, meaningful alternatives, operational consequences, and implementation evidence preserved together. Give each decision an explicit lifecycle status.

## What does not belong here
Temporary plans, task lists, investigations, and unaccepted proposals belong in [[70-planning/README|70-planning]]. Existing code alone does not prove that every incidental implementation choice was an intentional architecture decision.

## Naming convention
Use stable, sortable filenames such as `0001-short-title.md`. Keep the front-matter title globally unique and add the finished record to this index.

## Index
No decision records currently exist beyond [[ADR-template|the ADR template]]. Add entries here only after the decision record contains evidence and a declared status.

## Related documents

- [[ADR-template|ADR template]]
- [[70-planning/README|Planning workspace]]
- [[documentation-model|Documentation model]]
