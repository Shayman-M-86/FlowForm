---
title: FlowForm documentation
aliases: ["FlowForm documentation"]
document_type: overview
status: draft
authority: canonical
verified_against_commit: null
tags: [meta]
related_code: ["../scripts/docs/"]
related_docs: ["Project Knowledge", "Development workspace"]
---

# FlowForm documentation

FlowForm documentation separates what the system currently is from the work
that may change it. The tree provides one structural home for each subject,
while titles, related-document metadata, and wiki links connect concepts that
cross those ownership boundaries.

## Knowledge and ongoing work

[[project-knowledge-index|Project Knowledge]] contains maintained explanations
of FlowForm's product behaviour, software boundaries, data and security model,
infrastructure, operating concerns, engineering practices, and exact reference
facts. Its claims must come from current code, tests, schemas, configuration,
automation, or infrastructure definitions.

[[development-workspace-index|Development workspace]] contains the material
used to change that accepted understanding: decisions, plans, investigations,
research, experiments, migrations, and technical debt. Workspace content may
be incomplete or contested and does not become Project Knowledge merely by
being completed.

## How the documentation fits together

Folder heads provide the high-level model for a subject: its responsibilities,
boundaries, important concepts, and how its subcategories interact. Child
documents deepen one part of that explanation. Cross-links connect adjacent
subjects without duplicating their content. A head is therefore an overview in
its own right, not a directory listing.

Document metadata makes confidence visible. `status` distinguishes scaffolds,
drafts, and verified pages; `authority` distinguishes accepted knowledge from
working material; and `verified_against_commit` records the implementation
baseline actually inspected.

The previous documentation tree is retained under
`old-docs/documentation-v1/` as historical input. It is not a source of
current architecture without fresh implementation evidence.

## Related documents

- [[project-knowledge-index|Project Knowledge]]
- [[development-workspace-index|Development workspace]]
