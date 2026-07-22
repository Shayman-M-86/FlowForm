---
title: Documentation model
aliases:
  - "Documentation model"
document_type: overview
status: draft
authority: canonical
verified_against_commit: ed0fb65df856e18807ee243b4bca512a8d0442b0
tags: [meta]
related_code:
  - "../../scripts/docs/"
related_docs:
  - "FlowForm documentation home"
  - "Documentation generator guide"
  - "Planning workspace"
  - "Architecture decision records"
---

# Documentation model

Defines the layers, authority rules, and update expectations for FlowForm documentation.

## Source and authority

The current implementation is the source of truth. Claims in canonical documents must be checked against current code, tests, configuration, CI workflows, infrastructure definitions, or reproducible generated output. `old-docs/` is historical context only and is never sufficient evidence by itself.

A document's `authority` identifies its role, while `status` reports its maturity. `verified_against_commit` records the implementation baseline used for meaningful claims; it does not make unchecked sections verified.

## Documentation layers

| Layer                | Purpose                                                                                                                  | Boundary                                                                  |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------- |
| `00-overview/`       | Orient readers to the project, terminology, repository, and documentation model.                                         | Keep broad and direct readers to deeper material.                         |
| `10-architecture/`   | Describe stable runtime components, external systems, boundaries, relationships, deployment shape, and major data flows. | Avoid detailed code catalogues and speculative design.                    |
| `20-domains/`        | Explain one product or business domain's responsibilities, entities, invariants, dependencies, and open questions.       | Keep workflows and implementation references concise.                     |
| `30-workflows/`      | Trace an end-to-end process from trigger and preconditions through outputs, important failures, and verification.        | Link to scripts and configuration instead of copying them.                |
| `40-implementation/` | Map approved concepts and workflows to important directories, entry points, modules, tests, and generated boundaries.    | Do not document every file, class, or helper.                             |
| `50-decisions/`      | Preserve supported rationale and consequences for lasting architectural decisions.                                       | Plans and incidental technical choices are not ADRs.                      |
| `60-reference/`      | Store exact, concise, searchable facts such as commands, configuration locations, and catalogues.                        | Explanations belong in the relevant higher-level layer.                   |
| `70-planning/`       | Hold temporary plans, proposals, unfinished work, and unresolved design.                                                 | Planning content is not current architecture.                             |
| `90-generated/`      | Hold reproducible repository-derived output.                                                                             | State the generator and sources; do not edit generated sections manually. |

## Knowledge network conventions

The documentation is a connected network, not a collection of independent files. Three conventions build that network.

### Titles are identifiers

Every document declares a `title` in front matter. Titles are globally unique across `docs/` (case-insensitively) and are the canonical identifiers used by `related_docs` and documentation search. Each document also lists that exact title in its `aliases` front-matter property so it appears under that name in Obsidian's link suggestions. Use sentence case and prefer a name that is unambiguous on its own — for example `Backend implementation` rather than `Backend`, and `Testing workflow` rather than `Testing`.

### Wiki links

Documents reference each other with Obsidian-compatible wiki links whose target is the note filename and whose display text is normally the document title: `[[proxmox-rehearsal|Proxmox rehearsal implementation]]`. A unique filename stem is sufficient; when stems collide, use the shortest distinguishing path relative to `docs/`, such as `[[90-generated/README|Generated documentation]]`. Do not use a front-matter title as the link target when it differs from the filename: aliases assist link creation, but Obsidian stores a durable alias link using the real note target plus display text. Use wiki links only for documents under `docs/`; refer to code with plain repository paths in backticks. Every document lists its most useful neighbours in `related_docs` (front matter, as titles) and, except for short prose-navigation pages, in a closing `## Related documents` section.

Linking is cheap and encouraged: link a concept the first time a section mentions it, and prefer linking to the document that owns the explanation over restating it.

### Tags

`tags` is an optional front-matter list used only for cross-cutting classification that the directory layers do not already express. The controlled vocabulary is:

| Tag              | Classifies documents about                                  |
| ---------------- | ------------------------------------------------------------ |
| `backend`        | The Flask backend application                                |
| `frontend`       | The Studio and public-site frontend applications             |
| `infrastructure` | Hosting, images, containers, networking, and deployment      |
| `security`       | Authentication, access control, encryption, and trust        |
| `configuration`  | Configuration surfaces, secrets, and environment variables   |
| `ci-cd`          | Continuous integration and delivery                          |
| `tooling`        | Repository scripts, commands, and developer tooling          |
| `meta`           | The documentation system itself and planning/decision indexes |

Do not invent one-off tags. Add a new tag to this table only when it would classify several documents and support useful filtering; layer membership (`domain`, `workflow`, `reference`, …) is already captured by `document_type` and the directory, and must not be duplicated as a tag.

## Code linkage metadata

`related_code` records the implementation evidence boundary a document depends on. Entries are written relative to the document's own directory (the same convention as relative links) and may name an exact file, a directory (with a trailing `/`), or a glob (`*`, `?`, `[…]`). This linkage is what lets the documentation tooling map code changes onto the documents that may need review, so keep it selective and accurate rather than exhaustive.

Three optional fields refine that linkage; add them only when they earn their keep:

| Field             | Purpose                                                                                          |
| ----------------- | ------------------------------------------------------------------------------------------------ |
| `change_triggers` | Extra paths or globs that should flag the document for review even though they are not core evidence. Matched with lower confidence than `related_code`. |
| `exclusions`      | Paths or globs to subtract from the matched set, so a broad `related_code` directory can skip noisy sub-paths. |
| `code_confidence` | `high`, `medium`, or `low`; weights how strongly a matched change implicates the document.        |

The documentation tooling under `scripts/docs/docsys/` reads these fields to build the documentation index, detect impacted documents, and check freshness. The tooling never edits documents; it identifies what to review. Generated documents record their generator and sources instead of prose evidence, and are refreshed rather than hand-verified.

## Update discipline

Documentation work proceeds in narrow, reviewable stages. Inspect the target scaffold and implementation evidence, write only claims appropriate to that layer, record uncertainty instead of guessing, and use an independent review to remove unsupported claims and duplication. Stop at the stage boundary rather than filling adjacent scaffolds opportunistically.

When a file is added or renamed, update its wiki-link targets, navigation, and related-document metadata. When a title changes, update its matching `aliases` entry, wiki-link display text, and every `related_docs` entry that uses it. Validation reports unresolved note targets and metadata titles. When implementation changes invalidate a claim, update the document and its verification commit together.

## Validation

Run the current Stage 1 documentation checks from the repository root:

```sh
python3 scripts/docs/validate-doc-links.py
python3 scripts/docs/validate-doc-metadata.py
```

These checks cover local Markdown link targets, `[[wiki link]]` resolution, required front-matter fields, Obsidian title aliases, global title uniqueness, `related_docs` resolution, and the tag vocabulary. They do not establish that prose claims are correct; review against implementation evidence remains required.

The layered documentation tree and current `scripts/docs/` checks are uncommitted Stage 1 working-tree work at the recorded implementation baseline. Re-verify them and advance `verified_against_commit` after they are committed.
