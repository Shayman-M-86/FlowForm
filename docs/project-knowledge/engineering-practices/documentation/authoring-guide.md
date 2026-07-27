---
title: Documentation authoring guide
aliases: ["Documentation authoring guide"]
document_type: overview
status: draft
authority: canonical
verified_against_commit: null
tags: [meta]
related_code:
  - "../../../../scripts/docs/"
  - "../../../../AGENTS.md"
related_docs:
  - "Documentation practice"
  - "Documentation model"
  - "Documentation validation and review"
---

# Documentation authoring guide

Guides agents and scripts that update FlowForm documentation from verified
repository evidence. This guide and the documentation validators are tracked
repository content; a verification commit records the checked process and script
boundary, not the correctness of any generated prose.

## Required reading order

Before changing documentation:

1. Read the [[documentation-model|Documentation model]] to identify the target
   collection, branch, and its ownership boundary.
2. Read the target document and its linked neighbours.
3. Check repository-level and more specific `AGENTS.md` instructions that apply
   to the target path.

Do not use `old-docs/` as a source of current facts. It is historical material
whose claims require fresh implementation evidence.

## Agent context workflow

Codex and Claude share the `flowform-doc-context` skill and the
`flowform-docs` MCP server. Before non-trivial work, agents call
`get_task_context`, read only the primary documents it returns, and use the
returned implementation locations to target evidence inspection. After
behavioural or architectural changes, they call `get_impacted_docs` and review
the results rather than updating documentation mechanically.

`docs/` is the active context root. Every Docsys MCP tool accepts `docs_root`;
when it is omitted, Docsys selects that active tree. The matching Codex and
Claude `docs-maintainer` agents support bounded documentation updates and
evidence review. For parallel work, assign non-overlapping document and
evidence boundaries; the parent agent retains responsibility for integrated
links, navigation, and final validation.

## Evidence rules

Start with the source that owns the claim. Use tests to confirm contracts and
failure behaviour, configuration and CI for executable workflows, and
infrastructure definitions for deployment claims. A nearby README can help locate
evidence, but it does not override code or configuration.

Record relevant repository paths in `related_code`. Keep that list selective: it
should point a future reader to the main evidence boundary, not inventory every
file inspected.

## Claim classification

Use the collection and authority rules in the [[documentation-model|Documentation
model]]. In particular, keep proposals and unresolved design in the
[[development-workspace-index|Development workspace]], reserve Project Knowledge
for current behaviour, and mark missing evidence or contradictions instead of
turning assumptions into current behaviour. A completed plan does not
automatically become Project Knowledge: distil its durable findings into the
owning branch from implementation evidence, then archive the plan.

## Repeatable process

Work in one small group of documents that share a subject and evidence boundary:

1. Define what each page owns and what belongs in another branch. Write the
   folder head as the integrated high-level model before distributing detail
   among children.
2. Inspect the current code, tests, schemas, configuration, CI, or
   infrastructure that owns each claim.
3. Write the smallest useful explanation and link to pages that own adjacent
   detail.
4. Update front matter (including the title-matching Obsidian `aliases` entry),
   wiki links, and `related_docs` together.
5. Review the group for unsupported claims, repeated explanations, ownership
   leakage, and unresolved gaps.
6. Run the documentation validators from the repository root.

For every folder head, review the prose once without following its links. It
must explain the subject's purpose, boundaries, key concepts or lifecycle, and
the relationship between its subcategories. A heading followed only by child
links is navigation, not an overview. If no meaningful overview exists yet,
defer the branch instead of preserving an empty taxonomy.

Set `verified_against_commit` to the inspected commit for implementation-backed
prose. A commit value is an evidence baseline, not a substitute for review. Use
`null` when a page has not been checked against a committed implementation
baseline, including a scaffold, workspace page, or documentation process that
exists only in the working tree.

## Reference and navigation discipline

Follow the [[documentation-model|knowledge-network conventions]] for wiki links,
titles, `aliases`, `related_docs`, tags, and code paths. Wiki-link targets use
the actual note filename (or shortest distinguishing path), while their display
text and `related_docs` use the document title. When changing a filename or
title, run the validators immediately so unresolved links do not spread.

## Generated pages

For generated pages, change the generator rather than hand-editing generated
content. Generated documents record their generator and sources instead of prose
evidence, and are refreshed rather than hand-verified.

## Answering repository questions

When documentation work accompanies a repository answer, report what changed,
what was validated, the commit used for verification, and which documents remain
scaffold-only. Include contradictions or missing evidence rather than hiding them
in prose.

## Related documents

- [[documentation-index|Documentation practice]]
- [[documentation-model|Documentation model]]
- [[validation-and-review|Documentation validation and review]]
