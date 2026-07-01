---
type: Tool
title: flowform-repomap MCP server
description: FastMCP server orchestrating an iterative repo-summarisation workflow that writes per-directory rule files with `paths:` frontmatter.
resource: tools/mcp/repomap.py
tags: [mcp, tooling, documentation]
timestamp: 2026-07-01T00:00:00Z
---

# Overview

`repomap.py` drives an iterative summarisation loop: an agent calls
`get_next_path()`, summarises that directory, calls `save_summary()`, and
finally `build_map()` writes per-directory rule files into
`.claude/rules/repomap/` with `paths:` frontmatter so relevant context loads
only when needed. The path list driving the walk comes from
`.claude/repomap-config.json`.

Several concepts in this bundle (e.g. [backend/app/services/](/backend/services.md),
[Studio app](/apps/studio-app.md)) were sourced directly from
`.claude/rules/repomap/` output produced by this tool.

# Citations

[1] [.claude/rules/repomap/tools-mcp.md](../../.claude/rules/repomap/tools-mcp.md)
[2] [Root CLAUDE.md — flowform-repomap](../../CLAUDE.md)
