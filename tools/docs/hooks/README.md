# Agent hook lifecycle

Codex and Claude share one non-blocking quality hook implementation in this
directory. Documentation discovery is deliberate and has no lifecycle hook.

```text
Edit or Write
    |
    v
PostToolUse: post_tool_python_quality.py
  - ignore non-Python and non-backend files
  - run py_compile on an edited backend Python file
  - run a narrow Ruff safe-fix pass
  - never block the task
```

## Configuration

The `PostToolUse` entries in `.codex/hooks.json` and
`.claude/settings.json` intentionally match. `docsys_hook_lib.py` contains only
the shared input adapter and repository root used by that hook.
