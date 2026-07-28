# docsys — FlowForm documentation tooling

`docsys` treats the active `docs/` tree as a queryable knowledge network shared
between humans, AI agents, and the codebase. It does **not** generate more
prose documentation; it makes the existing documentation maintainable,
retrievable, and tightly coupled to development.

Guiding principles (see [`Documentation model`](../../../docs/project-knowledge/engineering-practices/documentation/documentation-model.md)):

- Code is the source of truth; documentation is a projection of understanding.
- Prefer many small, deterministic tools over one large AI-driven system.
- AI is used only by callers (agents, the MCP server) for interpretation and
  summarisation — never inside the core tools.
- Content changes remain explicit. The Git hook may only downgrade invalidated
  verification metadata and stage that small, reviewable change.

Everything here is standard-library only, so it runs anywhere `python3` does.

## Layout

| Module | Responsibility |
| --- | --- |
| `model.py` | Front-matter parser, `Document`/`DocSet` model, glob/path matching |
| `gitutil.py` | Defensive `git` wrappers (diffs, commit ranges, distance) |
| `config.py` | Optional `docsys.config.json` overrides |
| `index.py` | Builds `docs/project-knowledge/reference/generated/documentation-index.json` |
| `impact.py` | Maps code changes onto documents, ranks confidence, explains why |
| `evidence.py` | Calculates verification digests from staged or committed Git blobs |
| `freshness.py` | Compares recorded and current evidence digests |
| `query.py` | Deterministic ranked search |
| `context.py` | Smallest useful documentation context for a task / change |
| `retrieve.py` | Single-document and related-document retrieval |
| `validate.py` | Structured metadata/link findings (dashboard + programmatic use) |
| `markdown_ast.py` | Source-positioned structural Markdown parser |
| `debt.py` | Advisory complexity metrics and split-candidate analysis |
| `health.py` | Health report + generated `documentation-dashboard.md` |
| `propose.py` | Reviewable, agent-assisted update proposal packets |
| `ci.py` | CI documentation-review step (report + optional critical gate) |
| `mcp_server.py` | Dependency-free MCP server exposing the tools to agents |

## The index is the API

`documentation-index.json` is the primary interface every other tool and agent
uses instead of re-scanning `docs/`. Each entry carries the front matter,
resolved `related_code` patterns, headings, and the wiki-link graph for one
document. It is deterministic and safe to commit and diff.

```sh
python3 -m docsys index
```

## Command-line usage

Run from the repository root. The dispatcher `python3 -m docsys <cmd>` wraps
each tool; every tool also runs standalone (`python3 -m docsys.impact ...`).

```sh
# (Re)build the machine-readable index.
python3 -m docsys index

# What documentation might this change affect? (working tree, or a range)
python3 -m docsys impact
python3 -m docsys impact --base origin/main

# Which documents are drifting from the code they describe?
python3 -m docsys freshness

# After semantic review, record the exact staged implementation evidence.
python3 -m docsys evidence promote --staged docs/path.md

# Agent verification workflow: also stage the promoted documentation path.
python3 -m docsys evidence promote --staged --stage docs/path.md

# Repair dates in the working tree after a read-only pre-commit failure.
python3 -m docsys evidence sync-last-edited

# Read-only pre-commit checks.
python3 -m docsys evidence check-last-edited
python3 -m docsys evidence check-staged

# Ranked deterministic search.
python3 -m docsys query "response encryption locator"
python3 -m docsys search "networking" --collection project-knowledge

# Collection-aware structural validation and advisory debt analysis.
python3 -m docsys validate --profile editing
python3 -m docsys validate --profile commit
python3 -m docsys debt --changed --suggest-splits

# Smallest useful context for a task or a set of changed files.
python3 -m docsys context --task "add a new survey question type"
python3 -m docsys context --changed backend/app/routes/surveys.py

# Regenerate the health report and dashboard.
python3 -m docsys health

# Reviewable update proposals for an agent (never writes to docs/).
python3 -m docsys propose --base origin/main --markdown
```

> Note: because these are packaged modules, either run with the package on the
> path (`PYTHONPATH=tools/docs python3 -m docsys ...`) or from within
> `tools/docs/`. CI uses the `PYTHONPATH` form.

## MCP server

The MCP server is the preferred interface for AI agents. It speaks MCP's
JSON-RPC over stdio directly, with no third-party dependency.

```sh
claude mcp add flowform-docs -- \
  env PYTHONPATH=tools/docs python3 -m docsys.mcp_server
```

Tools exposed: `search_docs`, `get_document`, `get_related`,
`get_task_context`, `get_impacted_docs`, `check_freshness`,
`documentation_debt`, and `doc_health`. Every tool accepts an optional
`docs_root`. When omitted, Docsys selects `docs/`. Set
`FLOWFORM_DOCS_ROOT` to override that process-wide default.

`get_task_context` also returns `documentation_reliability`. This disclosure
signal combines each primary document's status, verification baseline,
freshness, and working-tree state. Callers must surface its message when
`requires_disclosure` is true; it does not replace checking material claims
against implementation evidence.

## Metadata the tooling reads

Beyond the required front matter, documents may declare optional linkage fields
(defined in the [documentation model](../../../docs/project-knowledge/engineering-practices/documentation/documentation-model.md)):

- `related_code` — files, directories (`trailing/`), or globs the document
  depends on, relative to the document.
- `change_triggers` — extra paths/globs that flag the document for review
  (lower confidence than `related_code`).
- `exclusions` — paths/globs to subtract from the matched set.
- `code_confidence` — `high` / `medium` / `low`, weighting impact and
  freshness.

`verified_evidence_digest` is maintained by `docsys evidence`, not by hand. It
is the SHA-256 digest of the staged Git blobs selected by `related_code` and
`change_triggers`, after `exclusions`. Documentation content is excluded, so
implementation, documentation, and verification metadata can be committed
together without a self-referential commit SHA. This applies only to Project
Knowledge; Development Workspace does not use evidence verification.

`last_edited` uses `YYYY-MM-DD`. Pre-commit checks the staged value but never
changes it. When the date is stale, run `docsys evidence sync-last-edited`,
review the working-tree update, and stage it explicitly.

## Configuration

Optional. Copy `tools/docs/docsys.config.example.json` to
`tools/docs/docsys.config.json` and override only the keys you need:

- `critical_doc_globs` — documents whose impact-but-not-modified state fails
  the CI `docs-review` job (empty by default, so CI never fails on docs).

## Commit integration

The repository Git pre-commit hook checks `last_edited`, verifies Project
Knowledge affected by staged implementation changes against the staged index,
and runs the `commit` validation profile. Every check is read-only. On failure,
Docsys prints the repair command and exits without changing the working tree or
index. Repair commands update the working tree; the author reviews and stages
those changes explicitly. Development Workspace bypasses evidence verification.
This workflow is intentionally not part of CI.

## Relationship to the existing validators

The dependency-free `validate-doc-links.py` and `validate-doc-metadata.py`
remain the canonical structural gate. `docsys.validate` exposes the same rules
programmatically for the dashboard; the two never disagree because both parse
the front matter the same way.
