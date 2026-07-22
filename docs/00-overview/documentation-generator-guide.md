---
title: Documentation generator guide
aliases:
  - "Documentation generator guide"
document_type: overview
status: draft
authority: canonical
verified_against_commit: ad26b87e9820
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

This guide and the documentation validators are tracked repository content. The
verification commit records the checked documentation process and script
boundary; it does not make generated prose or implementation claims correct.

## Required reading order

Before changing documentation:

1. Read [[README|the documentation home]] and this guide.
2. Read the [[documentation-model|Documentation model]] to identify the target layer and its boundary.
3. Read the target document and its linked neighbours.
4. Check repository-level and more specific `AGENTS.md` instructions that apply to the target path.

Do not use `old-docs/` as a source of current facts. It is historical material whose claims require fresh implementation evidence.

## Evidence rules

Start with the source that owns the claim. Use tests to confirm contracts and failure behaviour, configuration and CI for executable workflows, and infrastructure definitions for deployment claims. A nearby README can help locate evidence, but it does not override code or configuration.

Record relevant repository paths in `related_code`. Keep that list selective: it should point a future reader to the main evidence boundary, not inventory every file inspected.

## Claim classification

Use the layer and authority rules in the [[documentation-model|Documentation model]]. In particular,
keep proposals and unresolved design in [[70-planning/README|planning]], use
[[50-decisions/README|ADRs]] only for supported lasting decisions, and
mark missing evidence or contradictions instead of turning assumptions into
current behaviour.

## Repeatable process

Work in one small group of documents that share a subject and evidence boundary:

1. Define what each page owns and what belongs in another layer.
2. Inspect the current code, tests, schemas, configuration, CI, or infrastructure that owns each claim.
3. Write the smallest useful explanation and link to pages that own adjacent detail.
4. Update front matter (including the title-matching Obsidian `aliases` entry), wiki links, and `related_docs` together.
5. Review the group for unsupported claims, repeated explanations, layer leakage, and unresolved gaps.
6. Run the documentation validators from the repository root.

Set `verified_against_commit` to the inspected commit for implementation-backed prose. A commit value is an evidence baseline, not a substitute for review. Use `null` when a page has not been checked against a committed implementation baseline, including a scaffold, planning page, or documentation process that exists only in the working tree.

## Reference and navigation discipline

Follow the [[documentation-model|knowledge-network conventions]] for wiki links,
titles, `aliases`, `related_docs`, tags, and code paths. Wiki-link targets use
the actual note filename (or shortest distinguishing path), while their display
text and `related_docs` use the document title. When changing a filename or
title, run the validators immediately so unresolved links do not spread.

## Planning discipline

Keep temporary plans in [[70-planning/README|planning]]. A completed plan does
not automatically become architecture: update the appropriate canonical page
from implementation evidence, then move or retire the plan. For
[[90-generated/README|generated pages]], change the generator rather than
hand-editing generated content.

## Review checklist

For each completed group, check:

- every current-state claim has an implementation evidence path;
- metadata matches the document's actual maturity and scope;
- wiki links resolve to Obsidian note targets, while `related_docs` and `aliases` use the exact document title;
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

- [[README|FlowForm documentation home]]
- [[documentation-model|Documentation model]]
- [[90-generated/README|Generated documentation]]
- [[70-planning/README|Planning workspace]]
- [[50-decisions/README|Architecture decision records]]
