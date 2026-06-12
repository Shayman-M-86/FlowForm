---
name: source-command-repomap
description: Refresh FlowForm repo map from `.Codex/repomap-config.json`.
user-invocable: false
paths:
  - ".Codex/repomap-config.json"
  - ".claude/repomap.md"
  - ".claude/rules/**"
---

# Source Command Repomap

Use when user asks to run `repomap`.

## Steps

1. Read `.Codex/repomap-config.json`.
2. Call `start_session()`.
3. Spawn one parallel agent per config group.
4. Agent task:
   - inspect listed paths
   - skip generated files, lock files, `__pycache__`
   - read 2-3 representative files
   - return JSON only: `[{"path":"...","summary":"..."}]`
5. For each result, call `save_summary(path, summary)`.
6. Call `build_map()`.
7. Report group count, path count, output files.

## Shortcut

If `repomap.md` already exists and only split/import is needed, call
`import_from_repomap_md()`.
