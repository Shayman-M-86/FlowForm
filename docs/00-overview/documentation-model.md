---
title: Documentation model
document_type: overview
status: scaffold
authority: canonical
verified_against_commit: ac7d021ad3716a68638759df684b9a3c32bb4389
related_code: ["../../scripts/docs/"]
related_docs: ["../README.md", "documentation-generator-guide.md"]
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

## Update discipline

Documentation work proceeds in narrow, reviewable stages. Inspect the target scaffold and implementation evidence, write only claims appropriate to that layer, record uncertainty instead of guessing, and use an independent review to remove unsupported claims and duplication. Stop at the stage boundary rather than filling adjacent scaffolds opportunistically.

When a file is added or renamed, update navigation and related-document metadata. When implementation changes invalidate a claim, update the document and its verification commit together.

## Validation

Run the current Stage 1 documentation checks from the repository root:

```sh
python3 scripts/docs/validate-doc-links.py
python3 scripts/docs/validate-doc-metadata.py
```

These checks cover local Markdown link targets and required front-matter fields. They do not establish that prose claims are correct; review against implementation evidence remains required.

The layered documentation tree and `scripts/docs/` checks are uncommitted Stage 1 working-tree work at the recorded implementation baseline. Advance `verified_against_commit` after they are committed and re-verified.
