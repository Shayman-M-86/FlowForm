---
title: Engineering migrations
aliases: ["Engineering migrations"]
document_type: planning-index
status: draft
authority: working
verified_against_commit: null
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

## Related documents

- [[development-workspace-index|Development workspace]]
- [[planning-index|Engineering planning]]
- [[decisions-index|Engineering decisions]]
- [[archive-index|Engineering archive]]
