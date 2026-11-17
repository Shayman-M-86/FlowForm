---
title: Planning workspace
aliases:
  - "Planning workspace"
document_type: planning-index
status: draft
authority: planning
verified_against_commit: null
tags: [meta]
related_code: []
related_docs:
  - "Active plans"
  - "Completed plans"
  - "Abandoned plans"
  - "Architecture decision records"
  - "Documentation model"
---

# Planning workspace
Separates temporary documentation and implementation plans from canonical documentation.

## Purpose
Use this directory for active, completed, and abandoned plans that must remain distinguishable from current system truth. Planning documents may describe intended changes, but canonical documents describe only implemented and verified behaviour.

## Active plans
Place current planning notes in `active/` while work is ongoing. Give each plan a clear purpose, scope, evidence boundary, decisions needed, and exit criteria.

## Completed plans
Move finished plans to `completed/` when they remain useful as task history. Completion records that work ended; it does not make every proposal in the plan authoritative.

## Abandoned plans
Move intentionally discarded plans to `abandoned/` and explain the decision, including which assumptions or constraints invalidated the approach.

## Promotion rules
Promote only implemented current behaviour into canonical documentation and only supported durable choices into ADRs. Link back to the plan when its history remains useful.

## Related documents

- [[70-planning/active/README|Active plans]]
- [[70-planning/completed/README|Completed plans]]
- [[70-planning/abandoned/README|Abandoned plans]]
- [[50-decisions/README|Architecture decision records]]
- [[documentation-model|Documentation model]]
