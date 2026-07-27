---
title: Documentation practice
aliases: ["Documentation practice"]
document_type: overview
status: draft
authority: canonical
verified_against_commit: null
tags: [meta]
related_code:
  - "../../../../scripts/docs/"
related_docs:
  - "Engineering practices"
  - "Documentation model"
  - "Documentation authoring guide"
  - "Documentation validation and review"
---

# Documentation practice

Owns how FlowForm documentation itself is structured, authored, validated, and
reviewed. This branch is the governance home for the two-collection
documentation model: the rules a document must satisfy to enter Project
Knowledge, how agents and scripts author from implementation evidence, and how
the `docsys` tooling gates structure while keeping maintainability advisory.

```text
Documentation model
        |
        v
Authoring guide --> evidence-backed document --> validation profiles
        ^                    |                         |
        |                    v                         v
focused Docsys context   knowledge graph        review + debt signals
        |                                              |
        +---------------- maintained updates <---------+
```

## Governance model

Documentation quality has three separate parts. Structure gives every subject
one primary home and requires its folder head to explain the high-level model.
Evidence keeps current-state claims tied to implementation. Metadata makes the
document's authority, maturity, and verification baseline visible instead of
asking readers to infer confidence from tone.

Automation enforces objective defects such as missing heads, broken links,
duplicate titles, and collection-boundary violations. It does not decide
whether an overview explains its subject well, whether two pages repeat the
same concept, or whether a proposed split improves understanding. Those remain
content-review decisions.

## Authoring and review relationship

The [[documentation-model|Documentation model]] establishes the collections,
ownership tree, identity rules, and folder-head standard. The
[[authoring-guide|Documentation authoring guide]] turns that model into a
repeatable evidence-first workflow. [[validation-and-review|Documentation
validation and review]] defines the automated profiles and the human checks
that automation cannot replace.

A useful folder head should still teach the reader something when every child
link is removed. Child documents provide depth; they are not a substitute for
the head's explanation.

## Documents in this branch

- [[documentation-model|Documentation model]] — layers, collections, authority
  rules, and the knowledge-network conventions.
- [[authoring-guide|Documentation authoring guide]] — the repeatable process
  agents and scripts follow to write from verified evidence.
- [[validation-and-review|Documentation validation and review]] — the `docsys`
  profiles, the review checklist, and how debt findings stay advisory.

## Related documents

- [[engineering-practices-index|Engineering practices]]
- [[documentation-model|Documentation model]]
- [[authoring-guide|Documentation authoring guide]]
- [[validation-and-review|Documentation validation and review]]
