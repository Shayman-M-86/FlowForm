---
title: Documentation model
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

Every document declares a `title` in front matter. Titles are globally unique across `docs/` (case-insensitively) and are the canonical way to refer to a document. Use sentence case and prefer a name that is unambiguous on its own — for example `Backend implementation` rather than `Backend`, and `Testing workflow` rather than `Testing`.

### Wiki links

Documents reference each other with wiki links: `[[Title]]`, or `[[Title|display text]]` when the surrounding sentence needs different wording. Wiki links resolve by title, never by path, so files can move between layers without breaking references. Use wiki links only for documents under `docs/`; refer to code with plain repository paths in backticks. Every document lists its most useful neighbours in `related_docs` (front matter, as titles) and, except for short prose-navigation pages, in a closing `## Related documents` section.

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

## Update discipline

Documentation work proceeds in narrow, reviewable stages. Inspect the target scaffold and implementation evidence, write only claims appropriate to that layer, record uncertainty instead of guessing, and use an independent review to remove unsupported claims and duplication. Stop at the stage boundary rather than filling adjacent scaffolds opportunistically.

When a file is added or renamed, update navigation and related-document metadata. When a title changes, update every `[[wiki link]]` and `related_docs` entry that uses it — validation reports any that were missed. When implementation changes invalidate a claim, update the document and its verification commit together.

## Validation

Run the current Stage 1 documentation checks from the repository root:

```sh
python3 scripts/docs/validate-doc-links.py
python3 scripts/docs/validate-doc-metadata.py
```

These checks cover local Markdown link targets, `[[wiki link]]` resolution, required front-matter fields, global title uniqueness, `related_docs` resolution, and the tag vocabulary. They do not establish that prose claims are correct; review against implementation evidence remains required.

The layered documentation tree and current `scripts/docs/` checks are uncommitted Stage 1 working-tree work at the recorded implementation baseline. Re-verify them and advance `verified_against_commit` after they are committed.
