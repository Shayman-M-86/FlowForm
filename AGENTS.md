# FlowForm agent instructions
Purpose: Defines repository-wide rules for future agents working in FlowForm.

## Metadata
- document_type: agent-instructions
- status: scaffold
- authority: canonical
- verified_against_commit: null
- related_docs: docs/README.md, docs/00-overview/documentation-generator-guide.md

## Core rule
The implementation is the source of truth. Documentation may be incomplete, historical, or wrong until verified against source code, tests, configuration, CI, and infrastructure definitions.
TODO: Verify this against the current implementation.

## Documentation context (Docsys MCP)
Before meaningful implementation work — whenever existing FlowForm architecture, behaviour, workflows, or domain rules are relevant — call `get_task_context` on the `flowform-docs` MCP server to load focused context. Prefer this retrieval over broadly grepping documentation or reading large parts of the repository. The `flowform-doc-context` skill describes the full workflow.

- Available MCP tools: `search_docs`, `get_document`, `get_related`, `get_task_context`, `get_impacted_docs`, `check_freshness`, `doc_health`. (CLI equivalents live under `scripts/docs/docsys/`; run `python3 -m docsys <command>` with `scripts/docs` on `PYTHONPATH`.)
- Code, tests, schemas, configuration, and infrastructure remain the source of truth. Documentation provides focused context and implementation boundaries, not authority.
- Load only the documents returned as relevant; do not load the whole documentation tree.
- Treat `old-docs/` as historical, never as current architecture.
- Never manually edit generated documentation under `docs/90-generated/`; regenerate it instead.
- After behavioural or architectural changes, call `get_impacted_docs` and review each high-confidence result, updating docs only when documented behaviour, responsibilities, boundaries, invariants, or workflows actually changed.
- Skip this for trivial changes: spelling fixes, formatting, or isolated mechanical renames.

## Documentation rules
Read `docs/README.md` and `docs/00-overview/documentation-generator-guide.md` before updating documentation. Keep canonical, planning, reference, and generated documents separate.
TODO: Verify this against the current implementation.

## Historical documentation warning
Treat `old-docs/` as untrusted historical context. Do not copy claims from it unless every claim is re-verified against the current implementation.
TODO: Verify this against the current implementation.

## Correct behavior examples
Correct: inspect code before updating a domain document, cite verified paths, record the commit SHA, and update navigation. Correct: place temporary plans under `docs/70-planning/` instead of architecture docs.
TODO: Verify this against the current implementation.

## Incorrect behavior examples
Incorrect: invent ports, commands, architecture guarantees, or security behavior from memory. Incorrect: treat a plan as an accepted decision. Incorrect: leave scaffold files empty or title-only.
TODO: Verify this against the current implementation.

## Pull request expectations
Summaries should state what changed, what was validated, and whether any documentation remains scaffold-only. Documentation-only changes still require link and metadata validation when available.
TODO: Verify this against the current implementation.
