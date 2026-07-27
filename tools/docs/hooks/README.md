# Agent hook lifecycle

Codex and Claude use the same hook configuration and the shared implementations
in this directory. Hooks are non-blocking support automation; they do not
verify documentation, commit changes, or replace agent judgment.

```text
agent task starts
       |
       v
SessionStart
session_start_capture_base.py
  - capture HEAD once for the session
  - remember implementation files already dirty
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
       |
       v
agent attempts to finish
       |
       v
Stop
stop_doc_impact_review.py
  - compare task changes with the captured baseline
  - ignore pre-existing dirty files and documentation-only work
  - ask Docsys for high-confidence Project Knowledge impact
  - show one non-blocking review reminder when relevant
       |
       v
task finishes
```

## Shared support

`docsys_hook_lib.py` owns input normalization, session state, Git change
detection, fingerprints, and Docsys impact lookup for both agents.

`record_doc_review.py` is a manual helper rather than a configured lifecycle
hook. An agent may use it to record which impacted documents were updated or
left unchanged. State is stored under `.docsys/hook-state/`, which is ignored by
Git.

## Configuration

The hook maps in `.codex/hooks.json` and `.claude/settings.json` are intentionally
identical:

| Event | Matcher | Shared command |
| --- | --- | --- |
| `SessionStart` | all sessions | `session_start_capture_base.py` |
| `PostToolUse` | `Edit\|Write` | `post_tool_python_quality.py` |
| `Stop` | every finish attempt | `stop_doc_impact_review.py` |

`.claude/hooks/stop_doc_impact_review.py` is a compatibility-only forwarder for
tasks that cached the former path before this consolidation. It contains no
hook logic and may be removed once no old tasks remain.

The Git pre-commit hook is a separate workflow. It maintains documentation edit
dates, validates staged Project Knowledge evidence, and runs the documentation
commit profile.
