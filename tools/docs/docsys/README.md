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
- `research.py` starts a fresh Codex session that uses the same CLI commands
  and returns a schema-constrained cited answer.
- `command_catalog.py` owns command effects and the spawned research CLI policy;
  `capabilities.py` exposes that inventory as text or JSON.
- Impact, freshness, health, debt, validation, indexing, and evidence remain
  explicit command operations.

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

Documentation has no MCP surface. `docsys research` is the answer-oriented
entry point. Each call starts `codex exec` as a fresh ephemeral process in an
empty temporary workspace with temporary result files. Starting outside the
repository prevents project configuration, MCP servers, hooks, rules, and
skills from being discovered. The prompt supplies the absolute repository and
Docsys paths instead. The process ignores user config and rules, disables
memory use and generation, does not persist a session, and cannot use web,
apps, or subagents. It uses only `docsys find`, `docsys read`, and the narrow
read-only source tools defined by `command_catalog.py`. The prompt enforces that
executable policy; the read-only sandbox is the hard worktree boundary. The
installed Codex client owns authentication, and Docsys never reads or copies
its local authentication state. Docsys validates every returned citation
against the current worktree.

Use `docsys capabilities --format json` for the exact command effects, approved
research executables, allowed Docsys subcommands, local availability, and
resolved executable paths.

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
The agent-setup validator checks skill and root-rule mirrors, the command-first
research boundary, and the absence of documentation MCP, platform-specific
agents, rules, commands, and lifecycle hooks. It does not constrain unrelated
agent tooling.
