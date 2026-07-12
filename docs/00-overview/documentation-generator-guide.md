---
title: Documentation generator guide
document_type: overview
status: draft
authority: canonical
verified_against_commit: null
tags: [meta]
related_code:
  - "../../AGENTS.md"
  - "../../scripts/docs/"
related_docs:
  - "FlowForm documentation home"
  - "Documentation model"
  - "Generated documentation"
  - "Planning workspace"
  - "Architecture decision records"
---

# Documentation generator guide

Guides agents and scripts that update FlowForm documentation from verified repository evidence.

This guide and the current documentation validators are uncommitted working-tree
content. Its `verified_against_commit` remains `null` until that process is
committed and rechecked.

## Required reading order

Before changing documentation:

1. Read [[FlowForm documentation home|the documentation home]] and this guide.
2. Read the [[Documentation model]] to identify the target layer and its boundary.
3. Read the target document and its linked neighbours.
4. Check repository-level and more specific `AGENTS.md` instructions that apply to the target path.

Do not use `old-docs/` as a source of current facts. It is historical material whose claims require fresh implementation evidence.

## Evidence rules

Start with the source that owns the claim. Use tests to confirm contracts and failure behaviour, configuration and CI for executable workflows, and infrastructure definitions for deployment claims. A nearby README can help locate evidence, but it does not override code or configuration.

Record relevant repository paths in `related_code`. Keep that list selective: it should point a future reader to the main evidence boundary, not inventory every file inspected.

## Claim classification

Use the layer and authority rules in the [[Documentation model]]. In particular,
keep proposals and unresolved design in [[Planning workspace|planning]], use
[[Architecture decision records|ADRs]] only for supported lasting decisions, and
mark missing evidence or contradictions instead of turning assumptions into
current behaviour.

## Repeatable process

Work in one small group of documents that share a subject and evidence boundary:

1. Define what each page owns and what belongs in another layer.
2. Inspect the current code, tests, schemas, configuration, CI, or infrastructure that owns each claim.
3. Write the smallest useful explanation and link to pages that own adjacent detail.
4. Update front matter, wiki links, and `related_docs` together.
5. Review the group for unsupported claims, repeated explanations, layer leakage, and unresolved gaps.
6. Run the documentation validators from the repository root.

Set `verified_against_commit` to the inspected commit for implementation-backed prose. A commit value is an evidence baseline, not a substitute for review. Use `null` when a page has not been checked against a committed implementation baseline, including a scaffold, planning page, or documentation process that exists only in the working tree.

## Reference and navigation discipline

Follow the [[Documentation model|knowledge-network conventions]] for wiki links,
titles, `related_docs`, tags, and code paths. When adding or changing a title,
run the validators immediately so unresolved links do not spread.

## Planning discipline

Keep temporary plans in [[Planning workspace|planning]]. A completed plan does
not automatically become architecture: update the appropriate canonical page
from implementation evidence, then move or retire the plan. For
[[Generated documentation|generated pages]], change the generator rather than
hand-editing generated content.

## Review checklist

For each completed group, check:

- every current-state claim has an implementation evidence path;
- metadata matches the document's actual maturity and scope;
- wiki links and `related_docs` resolve by exact document title;
- controlled tags add cross-cutting value and do not repeat the layer;
- explanations are not duplicated across abstraction layers;
- uncertainties and contradictions remain visible;
- no unrelated scaffold was filled opportunistically.

Then run:

```sh
python3 scripts/docs/validate-doc-links.py
python3 scripts/docs/validate-doc-metadata.py
```

These checks validate structure and resolution, not factual correctness.

## Answering repository questions

When documentation work accompanies a repository answer, report what changed, what was validated, the commit used for verification, and which documents remain scaffold-only. Include contradictions or missing evidence rather than hiding them in prose.

## Related documents

- [[FlowForm documentation home]]
- [[Documentation model]]
- [[Generated documentation]]
- [[Planning workspace]]
- [[Architecture decision records]]
