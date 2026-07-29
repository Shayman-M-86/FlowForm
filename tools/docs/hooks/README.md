# Agent hook lifecycle

Codex and Claude use the same hook configuration and the shared implementations
in this directory. Hooks are non-blocking support automation; they do not
verify documentation, commit changes, or replace agent judgment.

```text
agent task starts
       |
       v
SessionStart
session_start_doc_suggestion.py
  - suggest focused documentation context once
       |
       v
agent reads, reasons, and uses tools
       |
       +---- Edit or Write --------------------------------------+
       |                                                         |
       |    PostToolUse                                          |
       |    post_tool_python_quality.py                           |
       |      - ignore non-Python and non-backend files           |
       |      - run py_compile on an edited backend Python file   |
       |      - run a narrow Ruff safe-fix pass                   |
       |      - never block the task                              |
       |                                                         |
       +<--------------------------------------------------------+
```

## Shared support

`docsys_hook_lib.py` owns input normalization and session state. Its impact
helpers remain available to the unconfigured manual review utilities.

`record_doc_review.py` is a manual helper rather than a configured lifecycle
hook. An agent may use it to record which impacted documents were updated or
left unchanged. State is stored under `.docsys/hook-state/`, which is ignored by
Git.

## Configuration

The hook maps in `.codex/hooks.json` and `.claude/settings.json` are
intentionally identical:

| Event | Matcher | Shared command |
| --- | --- | --- |
| `SessionStart` | all starts; suggestion emitted once per session | `session_start_doc_suggestion.py` |
| `PostToolUse` | `Edit\|Write` | `post_tool_python_quality.py` |

`stop_doc_impact_review.py`, `record_doc_review.py`, and the compatibility
forwarder under `.claude/hooks/` are not configured lifecycle hooks. They
remain available only for older tasks that cached the former setup.

The Git pre-commit hook is a separate, read-only workflow. It checks
documentation edit dates, validates staged Project Knowledge evidence, and runs
the documentation commit profile without changing or staging files.
