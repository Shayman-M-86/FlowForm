# Shared agent hooks

Codex and Claude run the same non-blocking backend Python quality hook after
file edits. Documentation discovery and maintenance have no lifecycle hooks.

The hook configurations point to `post_tool_python_quality.py`; the input
adapter accepts either agent's payload format.
