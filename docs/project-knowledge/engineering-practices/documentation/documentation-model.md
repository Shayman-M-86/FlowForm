---
title: Documentation model
aliases: ["Documentation model"]
document_type: overview
status: draft
authority: canonical
verified_against_commit: null
tags: [meta]
related_code:
  - "../../../../scripts/docs/"
related_docs:
  - "Documentation practice"
  - "Documentation authoring guide"
  - "Documentation validation and review"
  - "Project Knowledge"
  - "Development workspace"
---

# Documentation model

Defines the collections, authority rules, structural conventions, and update
expectations for FlowForm documentation.

## Source and authority

The current implementation is the source of truth. Claims in canonical documents
must be checked against current code, tests, configuration, CI workflows,
infrastructure definitions, or reproducible generated output. Historical
material under `old-docs/` is context only and is never sufficient evidence by
itself.

A document's `authority` identifies its role, while `status` reports its
maturity. `verified_against_commit` records the implementation baseline used for
meaningful claims; it does not make unchecked sections verified.

When a material contradiction with implementation evidence is confirmed, the
owning document returns to `status: draft` and its
`verified_against_commit` is cleared until the corrected claims are checked
against a commit. Retrieval tools expose provisional and unreliable context so
agents can disclose uncertainty before using it.

## Two collections

The documentation filesystem is a single-parent knowledge tree with two explicit
collections:

- **Project Knowledge** (`project-knowledge/`) holds accepted, maintained
  understanding of FlowForm. It becomes strict at commit and CI validation
  boundaries. Documents here describe current behaviour, carry
  `authority: canonical`, and must not present proposals as established fact.
- **Development workspace** (`development-workspace/`) holds active work —
  decisions, plans, investigations, migrations, and technical debt. It uses
  lighter, editing-time enforcement. Workspace documents must not claim
  canonical authority, and honest incompleteness is acceptable.

Membership is derived from the physical tree: the first path segment under the
documentation root selects the collection. A document outside both collections
is invalid once the collection model is active.

```text
docs/
|-- docs-index.md
|-- project-knowledge/          canonical current understanding
|   |-- project-knowledge-index.md
|   `-- <subject>/<subject>-index.md
`-- development-workspace/     working and historical change material
    |-- development-workspace-index.md
    `-- <work-type>/<work-type>-index.md

folder head --> child documents --> nested folder heads
      |                |
      +---- one structural parent for every authored document
```

## Structural conventions

Every directory containing authored Markdown has a `<folder-name>-index.md`
folder head; for example, `backend/backend-index.md`. The head defines that
branch's ownership and is the structural parent of the documents and nested
folder heads beneath it. Every non-root document therefore has exactly one
inferable structural parent.

A folder head is a substantive overview, not a table of contents. It explains
the subject's purpose, responsibilities, boundaries, important concepts or
lifecycle, and how its subcategories interact. Links then offer deeper detail.
Removing the links should still leave a useful high-level understanding.

Do not create a directory solely to reserve a possible future category. Add a
branch when its head can explain a meaningful ownership boundary. A temporary
scaffold may exist during an active authoring pass, but it remains unfinished
until its subject, boundary, and evidence are meaningfully documented.

Cross-tree relationships use stable, globally unique titles and `related_docs`;
the model does not introduce a second `id` identity. A file may be promoted to
`topic/topic-index.md` when it develops independently useful children, while
keeping its title stable. Generated indexes and reports remain derived output
and never become the authored source of truth.

## Knowledge network conventions

The documentation is a connected network, not a collection of independent files.
Three conventions build that network.

### Titles are identifiers

Every document declares a `title` in front matter. Titles are globally unique
across the tree (case-insensitively) and are the canonical identifiers used by
`related_docs` and documentation search. Each document also lists that exact
title in its `aliases` front-matter property so it appears under that name in
Obsidian's link suggestions. Use sentence case and prefer a name that is
unambiguous on its own — for example `Backend implementation` rather than
`Backend`, and `Testing workflow` rather than `Testing`.

### Wiki links

Documents reference each other with Obsidian-compatible wiki links whose target
is the note filename and whose display text is normally the document title:
`[[documentation-model|Documentation model]]`. A unique filename stem is
sufficient; when stems collide, use the shortest distinguishing path relative to
the documentation root. Do not use a front-matter title as the link target when
it differs from the filename. Use wiki links only for documents inside the
documentation tree; refer to code with plain repository paths in backticks.
Every document lists its most useful neighbours in `related_docs` (front matter,
as titles) and in a closing `## Related documents` section. These links
supplement the document's explanation; they do not replace it.

Linking is cheap and encouraged: link a concept the first time a section
mentions it, and prefer linking to the document that owns the explanation over
restating it.

### Tags

`tags` is an optional front-matter list used only for cross-cutting
classification that the collection branches do not already express. The
controlled vocabulary is:

| Tag              | Classifies documents about                                    |
| ---------------- | ------------------------------------------------------------- |
| `backend`        | The Flask backend application                                 |
| `frontend`       | The Studio and public-site frontend applications             |
| `infrastructure` | Hosting, images, containers, networking, and deployment       |
| `security`       | Authentication, access control, encryption, and trust         |
| `configuration`  | Configuration surfaces, secrets, and environment variables    |
| `ci-cd`          | Continuous integration and delivery                           |
| `tooling`        | Repository scripts, commands, and developer tooling           |
| `meta`           | The documentation system itself and planning/decision indexes |

Do not invent one-off tags. Add a new tag to this table only when it would
classify several documents and support useful filtering; `document_type` and the
branch already capture role and ownership, and must not be duplicated as a tag.

## Code linkage metadata

`related_code` records the implementation evidence boundary a document depends
on. Entries are written relative to the document's own directory (the same
convention as relative links) and may name an exact file, a directory (with a
trailing `/`), or a glob (`*`, `?`, `[…]`). This linkage is what lets the
documentation tooling map code changes onto the documents that may need review,
so keep it selective and accurate rather than exhaustive.

Three optional fields refine that linkage; add them only when they earn their
keep:

| Field             | Purpose                                                                                                                                                  |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `change_triggers` | Extra paths or globs that should flag the document for review even though they are not core evidence. Matched with lower confidence than `related_code`. |
| `exclusions`      | Paths or globs to subtract from the matched set, so a broad `related_code` directory can skip noisy sub-paths.                                           |
| `code_confidence` | `high`, `medium`, or `low`; weights how strongly a matched change implicates the document.                                                              |

The documentation tooling under `scripts/docs/docsys/` reads these fields to
build the documentation index, detect impacted documents, and check freshness.
The tooling never edits documents; it identifies what to review. Generated
documents record their generator and sources instead of prose evidence, and are
refreshed rather than hand-verified.

All Docsys MCP retrieval and reporting tools accept an explicit documentation
root. The default is `docs/`, keeping agent context, impact review, freshness,
health, and debt analysis on one coherent tree.

## Update discipline

Documentation work proceeds in narrow, reviewable stages. Inspect the target
scaffold and implementation evidence, write only claims appropriate to that
branch, record uncertainty instead of guessing, and use an independent review to
remove unsupported claims and duplication. Stop at the stage boundary rather than
filling adjacent scaffolds opportunistically.

When a file is added or renamed, update its wiki-link targets, navigation, and
related-document metadata. When a title changes, update its matching `aliases`
entry, wiki-link display text, and every `related_docs` entry that uses it. When
implementation changes invalidate a claim, update the document and its
verification commit together.

See [[authoring-guide|Documentation authoring guide]] for the repeatable
authoring process and [[validation-and-review|Documentation validation and
review]] for the validation profiles and review checklist.

## Related documents

- [[documentation-index|Documentation practice]]
- [[authoring-guide|Documentation authoring guide]]
- [[validation-and-review|Documentation validation and review]]
- [[project-knowledge-index|Project Knowledge]]
- [[development-workspace-index|Development workspace]]
