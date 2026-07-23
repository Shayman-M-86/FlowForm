# docsys — FlowForm documentation tooling

`docsys` treats the `docs/` tree as a queryable knowledge network shared
between humans, AI agents, and the codebase. It does **not** generate more
prose documentation; it makes the existing documentation maintainable,
retrievable, and tightly coupled to development.

Guiding principles (see [`Documentation model`](../../../docs/00-overview/documentation-model.md)):

- Code is the source of truth; documentation is a projection of understanding.
- Prefer many small, deterministic tools over one large AI-driven system.
- AI is used only by callers (agents, the MCP server) for interpretation and
  summarisation — never inside the core tools.
- The tooling proposes and surfaces; it never silently rewrites documentation.

Everything here is standard-library only, so it runs anywhere `python3` does.

## Layout

| Module | Responsibility |
| --- | --- |
| `model.py` | Front-matter parser, `Document`/`DocSet` model, glob/path matching |
| `gitutil.py` | Defensive `git` wrappers (diffs, commit ranges, distance) |
| `config.py` | Optional `docsys.config.json` overrides |
| `index.py` | Builds `docs/90-generated/documentation-index.json` |
| `impact.py` | Maps code changes onto documents, ranks confidence, explains why |
| `freshness.py` | Classifies documents against `verified_against_commit` |
| `query.py` | Deterministic ranked search |
| `context.py` | Smallest useful documentation context for a task / change |
| `retrieve.py` | Single-document and related-document retrieval |
| `validate.py` | Structured metadata/link findings (dashboard + programmatic use) |
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

# Ranked deterministic search.
python3 -m docsys query "response encryption locator"

# Smallest useful context for a task or a set of changed files.
python3 -m docsys context --task "add a new survey question type"
python3 -m docsys context --changed backend/app/routes/surveys.py

# Regenerate the health report and dashboard.
python3 -m docsys health

# Reviewable update proposals for an agent (never writes to docs/).
python3 -m docsys propose --base origin/main --markdown
```

> Note: because these are packaged modules, either run with the package on the
> path (`PYTHONPATH=scripts/docs python3 -m docsys ...`) or from within
> `scripts/docs/`. CI uses the `PYTHONPATH` form.

## MCP server

The MCP server is the preferred interface for AI agents. It speaks MCP's
JSON-RPC over stdio directly, with no third-party dependency.

```sh
claude mcp add flowform-docs -- \
  env PYTHONPATH=scripts/docs python3 -m docsys.mcp_server
```

Tools exposed: `search_docs`, `get_document`, `get_related`,
`get_task_context`, `get_impacted_docs`, `check_freshness`, `doc_health`.

## Metadata the tooling reads

Beyond the required front matter, documents may declare optional linkage fields
(defined in the [documentation model](../../../docs/00-overview/documentation-model.md)):

- `related_code` — files, directories (`trailing/`), or globs the document
  depends on, relative to the document.
- `change_triggers` — extra paths/globs that flag the document for review
  (lower confidence than `related_code`).
- `exclusions` — paths/globs to subtract from the matched set.
- `code_confidence` — `high` / `medium` / `low`, weighting impact and
  freshness.

## Configuration

Optional. Copy `scripts/docs/docsys.config.example.json` to
`scripts/docs/docsys.config.json` and override only the keys you need:

- `critical_doc_globs` — documents whose impact-but-not-modified state fails
  the CI `docs-review` job (empty by default, so CI never fails on docs).
- `stale_commit_distance` — commit distance beyond which a verified document is
  flagged for review even if no owned code changed.

## CI integration

The `docs-review` job in `.github/workflows/ci.yml` validates documentation
structure, then posts a documentation-impact comment on pull requests
identifying affected documents and whether they were modified in the PR. It is
advisory: it fails only when a configured critical document is impacted but
left unmodified.

## Relationship to the existing validators

The dependency-free `validate-doc-links.py` and `validate-doc-metadata.py`
remain the canonical structural gate. `docsys.validate` exposes the same rules
programmatically for the dashboard; the two never disagree because both parse
the front matter the same way.
