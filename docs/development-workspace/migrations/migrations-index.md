---
title: Engineering migrations
aliases: ["Engineering migrations"]
document_type: planning-index
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-11-19
tags: [meta]
related_code: []
related_docs: ["Development workspace"]
---

# Engineering migrations

Engineering migrations document bounded movement from one known state or
contract to another. They hold migration design, execution notes, validation,
rollback considerations, and completion evidence while that change is active.

## Boundary

A migration is not the permanent owner of the resulting architecture or
operational workflow. It may describe temporary compatibility, sequencing, and
cutover conditions, but must not present those transitional measures as durable
Project Knowledge. General future work belongs in planning; a durable choice is
recorded in decisions.

## Lifecycle

Maintain the starting state, target state, completion criteria, and any open
risks as the work progresses. On completion, update the appropriate maintained
documentation from implementation evidence, then archive the migration record
when it no longer governs active work.

```text
known start --> transition steps --> compatibility window --> target state
     |                |                     |                    |
 evidence       validation gates       rollback boundary     completion evidence
                                                               |
                                              update maintained documentation
                                                               |
                                                        archive record
```

## V2 data definitions

- [[flowform-v2-survey-document-definition|FlowForm V2 survey document definition]]
- [[flowform-v2-answer-data-definition|FlowForm V2 answer data definition]]

## Active migrations

- [[declarative-data-and-typing|Declarative data and typing migration]]

- [[staging-hybrid-cutover|Staging cutover to the Proxmox hybrid stack]]
- [[survey-document-reconciliation-plan|Survey document reconciliation plan]]
- [[survey-document-visual-guide|Survey document visual guide]]
- [[survey-document-data-structure|Survey document data structure comparison]]
- [[survey-document-model-reference|Survey document model reference]]

## Related documents

- [[development-workspace-index|Development workspace]]
- [[planning-index|Engineering planning]]
- [[decisions-index|Engineering decisions]]
- [[archive-index|Engineering archive]]
