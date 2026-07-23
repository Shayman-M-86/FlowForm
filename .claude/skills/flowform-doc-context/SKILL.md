---
name: flowform-doc-context
description: Load focused FlowForm documentation context via the Docsys MCP server before non-trivial implementation, planning, or architecture work.
user-invocable: true
paths:
  - "docs/**"
  - "scripts/docs/docsys/**"
---

# FlowForm Doc Context

Use before meaningful work when existing FlowForm architecture, behaviour,
workflows, or domain rules matter: unfamiliar areas, architecture work, auth,
survey versioning, respondent links and submissions, response encryption,
core/response DB boundaries, deployment and infrastructure, cross-domain
refactors, and implementation planning.

Skip for trivial changes: spelling, formatting, isolated mechanical renames.

Tools are on the `flowform-docs` MCP server. Do not load the whole docs tree.

## Workflow

1. Turn the request into one concise retrieval query (the concepts/domains
   involved, not the literal task sentence).
2. Call `get_task_context` with that query (and `changed_files` if you already
   know them). It returns primary docs, neighbours, implementation paths,
   workflows, and open questions.
3. Read the **primary documents** it returns.
4. Read **neighbouring documents** only when a primary doc is insufficient.
5. Use the returned **implementation paths** to decide which code to inspect —
   let them target your reading instead of grepping broadly.
6. Treat documentation as context, not truth. Verify important claims against
   code, tests, schemas, configuration, or infrastructure.
7. If documentation and code disagree, report the contradiction; do not
   silently pick one.
8. Continue with planning or implementation.
9. After behavioural or architectural changes, call `get_impacted_docs`
   (base = the task's starting point, or the working tree).
10. Review each high/medium-confidence result and decide whether documentation
    actually needs updating — only when documented behaviour, responsibilities,
    boundaries, invariants, or a workflow changed. Otherwise record why not.

## Supporting tools

- `search_docs` — find docs when you are unsure which to retrieve.
- `get_document` / `get_related` — pull one document or its neighbours by title.
- `check_freshness` / `doc_health` — see which docs are drifting or unhealthy.

## Boundaries

- Code, tests, schemas, config, and infrastructure are the source of truth.
- `old-docs/` is historical, never current architecture.
- Never hand-edit generated docs under `docs/90-generated/`; regenerate them.
- Load only what is returned as relevant.
