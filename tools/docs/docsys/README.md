# Docsys internals

Docsys is FlowForm's dependency-free documentation discovery, retrieval,
impact, validation, health, and evidence library. The supported human and
agent entrypoint is:

```sh
tools/docs/bin/docsys --help
```

Exact commands, flags, defaults, and output formats are owned by command help.
This page records only the stable implementation boundaries.

## Architecture

- `model.py` loads the active documentation tree and enforces metadata and
  exact-file `related_code` conventions.
- `contracts.py` owns bounded find/read requests and response projections.
- CLI commands construct those contracts and print compact text or JSON.
- `mcp_server.py` is a thin read-only adapter over the same contracts and
  returns source line bounds for retrieved content.
- Impact, freshness, health, debt, validation, indexing, and evidence remain
  explicit CLI operations.

Document loading is lazy: displaying CLI help or initializing the MCP server
does not scan `docs/`.

## Discovery

`find` is deliberately narrow. It returns three results by default, requires
all significant terms unless the caller opts into broader matching, and does
not load neighbours or document bodies. Title, path, heading, tag, and exact
code-file matches outrank body-only matches.

`read` accepts an exact documentation path. Its default response is metadata
and headings; section and body content are explicit and bounded. Content
responses include one-based repository source lines so a research agent can
return checkable citations without rereading the document through a shell.

The MCP server advertises only `find` and `read`. Maintenance and mutation
operations are CLI-only.

The `flowform-research` MCP server is the answer-oriented entry point. Each call
starts `codex exec` as a fresh ephemeral process in an empty temporary working
directory. It ignores user config and rules, disables memory use and generation,
does not persist a session, and cannot use shell, web, apps, or subagents. The
installed Codex client owns authentication; Docsys never reads or copies its
local authentication state.

The private child-process MCP surface exposes only `find`, `read`,
`search_source`, and `read_source`. Source retrieval is limited to bounded text
ranges from tracked or visible non-ignored repository files and excludes secret
files, agent instructions, local state, dependencies, build output, and
historical documentation. The service validates every returned citation against
the current worktree before returning the structured result to its caller.

## Evidence and linkage

- `related_code` contains exact existing repository files. Directories and
  globs are invalid.
- `change_triggers` may contain broader paths or globs used only to suggest
  impact review.
- `exclusions` subtract matches from those review signals.
- `verified_evidence_digest` is maintained by `docsys evidence`, never by
  hand.

Implementation, tests, configuration, and automation remain authoritative.
Document status is disclosed in results but does not replace relevance
ordering.

## Validation

Run focused unit tests and the documentation validators after changing Docsys.
The agent-setup validator checks skill mirrors, MCP registration and schema
bounds, and the absence of documentation startup injection. It deliberately
does not constrain unrelated hooks or agent models.
