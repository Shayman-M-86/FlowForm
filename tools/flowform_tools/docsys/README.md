# Docsys internals

Docsys is FlowForm's documentation discovery, retrieval, impact, staged review,
validation, health, and evidence library. Its hook-critical core stays
dependency-free;
request contracts use the `docs` extra and agent research uses the separate
`research` extra. The supported command entrypoint is:

```sh
tools/bin/docsys --help
```

Exact commands, flags, defaults, and output formats are owned by command help.
This page records only the stable implementation boundaries.

## Architecture

- `core/model.py` loads the active documentation tree and enforces metadata and
  exact-file `related_code` conventions.
- `contracts.py` owns bounded find/read requests and response projections.
- `commands/` contains CLI entry points that print compact text or JSON.
- `commands/research.py` is the thin compatibility CLI for one research request.
- `research/` owns request/result contracts, prompts, the pre-warmed Claude SDK
  session pool, the one-tool MCP server, and the isolated Codex fallback.
- `command_catalog.py` owns command effects and the spawned research CLI policy;
  `commands/capabilities.py` exposes that inventory as text or JSON.
- `review` correlates staged impact provenance with evidence freshness,
  complexity debt, validation findings, and graph connectivity. Impact,
  freshness, health, debt, validation, indexing, and evidence remain explicit
  command operations.

Document loading is lazy: displaying CLI help does not scan `docs/`.

## Discovery

`find` is deliberately narrow. It returns three results by default, requires
all significant terms unless the caller opts into broader matching, and does
not load neighbours or document bodies. Title, path, heading, tag, and exact
code-file matches outrank body-only matches.

`read` accepts an exact documentation path. Its default response is metadata
and headings; section and body content are explicit and bounded. Content
responses include one-based repository source lines so a research agent can
return checkable citations without rereading the document through a shell.

Documentation exposes one answer-oriented MCP tool: `research`. Its server
lifespan pre-connects one Sonnet and one Opus `ClaudeSDKClient` without sending
a model prompt. A request consumes the matching client exactly once. While that
request runs, the pool initializes its replacement; after the result, the used
client is disconnected and its temporary workspace is removed. Independent
questions therefore do not share conversation context.

The SDK launches the installed Claude Code CLI through a Bubblewrap wrapper,
so it can use the existing local account login while the repository remains
read-only. Safe mode disables project and user customizations, session
persistence is disabled, inherited MCP servers are rejected, and provider API
or cloud credential variables are removed. The researcher can use only
`docsys find`, `docsys read`, and the narrow read-only source tools defined by
`command_catalog.py`. If Claude cannot complete a request, a fresh ephemeral
Codex process runs with its existing local login and read-only sandbox. Docsys
validates every returned citation against the current worktree.

`docsys research` remains a non-warm compatibility entry point. It creates one
SDK client for that invocation and applies the same Claude-first, Codex-fallback
policy.

This server is local developer automation. It is not a supported boundary for
offering other users access through personal Claude subscription credentials.

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
The agent-setup validator checks skill and root-rule mirrors, the single-tool
research MCP boundary, local runtime requirements, and the absence of
platform-specific documentation agents, rules, commands, and lifecycle hooks.
It does not constrain unrelated agent tooling.
