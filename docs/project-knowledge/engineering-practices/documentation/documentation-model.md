---
title: Documentation model
aliases: ["Documentation model"]
document_type: overview
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-08-03
tags: [meta]
related_code:
  - "../../../../tools/flowform_tools/docsys/model.py"
change_triggers:
  - "../../../../tools/"
related_docs:
  - "Documentation practice"
  - "Documentation workflow"
  - "Project Knowledge"
  - "Development workspace"
---

# Documentation model

FlowForm keeps current understanding separate from the material used to change
it. The implementation remains the source of truth; documentation provides a
maintained model of responsibilities, boundaries, and durable behaviour.

## Collections and authority

- **Project Knowledge** describes accepted current behaviour. Its pages are
  canonical and eligible for deliberate evidence-backed verification.
  Structural rules gate at commit and CI; exact evidence drift gates verified
  pages during commit.
- **Development Workspace** contains decisions, plans, investigations,
  migrations, debt, and historical work. It may be incomplete and is never
  promoted as verified current behaviour.

Historical material, including `old-docs/`, may explain intent but cannot
establish present behaviour. When implementation contradicts Project Knowledge,
correct the page, return it to `draft`, and clear its evidence digest.

## Shape of the tree

Every authored directory has a `<folder-name>-index.md` head. The head explains
the branch's ownership and high-level model; child pages exist only when a
subject has independently useful detail. Do not create branches as placeholders
or keep a child page merely because an older structure had one.

Each fact has one primary home. Cross-links connect adjacent owners without
copying their explanations. Exact commands and configuration belong beside the
implementation; generated inventories are outputs, not authored knowledge.

## Identity and links

Every document has a globally unique sentence-case `title` and a matching
`aliases` entry. `related_docs` stores document titles. Wiki links target the
note filename and normally display the title.

Tags are optional cross-cutting labels from the controlled vocabulary:
`backend`, `frontend`, `infrastructure`, `security`, `configuration`, `ci-cd`,
`tooling`, and `meta`. The directory tree already expresses ownership, so tags
should not repeat it without adding retrieval value.

## Evidence metadata

`status` exposes maturity: `scaffold`, `draft`, or `verified`.
`verified_evidence_digest` records the staged implementation baseline reviewed
for a Project Knowledge page; it is null everywhere else. `last_edited` is an
ISO date maintained through the commit workflow.

`related_code` contains only selective, exact, existing repository files that
own material claims. Directories and globs are invalid. Broader paths may appear
in `change_triggers` when a change should prompt review without claiming that
every file is evidence. `exclusions` may narrow those broad triggers.

Evidence linkage should make review more precise, not bind an overview to an
entire subsystem. A page with no stable exact evidence can remain a draft with
review triggers until a useful evidence boundary is identified.

## Maintenance rule

Prefer fewer pages with clear ownership over exhaustive catalogues. Consolidate
when pages share an owner, lifecycle, and change cadence. Split only when the
parts are independently useful and maintained from different evidence.

See [[documentation-workflow|Documentation workflow]] for the authoring,
validation, and verification process.

## Related documents

- [[documentation-index|Documentation practice]]
- [[documentation-workflow|Documentation workflow]]
- [[project-knowledge-index|Project Knowledge]]
- [[development-workspace-index|Development workspace]]
