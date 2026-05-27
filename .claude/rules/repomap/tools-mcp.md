---
paths: tools/mcp/**
---

# tools/mcp/

_Last updated: 2026-05-27 by /repomap_

Two FastMCP servers for local developer tooling. `flowform_dev.py` wraps the running backend's OpenAPI spec as MCP discovery tools (`list_endpoints`, `find_endpoints`, `describe_endpoint`, `describe_schema`, `list_endpoint_errors`) so Claude can navigate the API contract without reading source; it authenticates outgoing calls via Auth0 Device Authorization Flow implemented in `auth.py`, which caches AES-GCM-encrypted tokens at `~/.config/flowform/token.json` and supports silent token refresh. `repomap.py` is a second MCP server that orchestrates an iterative repo-summarisation workflow — Claude calls `get_next_path()`, summarises it, calls `save_summary()`, and finally `build_map()` writes per-directory rule files into `.claude/rules/repomap/` with `paths:` frontmatter; the path list is driven by `.claude/repomap-config.json`.
