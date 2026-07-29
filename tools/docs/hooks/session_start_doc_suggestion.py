#!/usr/bin/env python3
"""Shared SessionStart hook: suggest focused documentation context once.

On the first start for a session, give the agent one non-blocking suggestion
to load focused documentation when relevant. Writes lightweight per-session
state and never blocks or alters the session.

Input (stdin JSON) includes ``session_id`` and ``source``. Plain text output is
added as agent context by Codex and Claude. The hook succeeds (exit 0) even on
error, so it can never disrupt a session.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from docsys_hook_lib import (  # noqa: E402
    load_state,
    read_hook_input,
    resolve_session_id,
    save_state,
)

DOC_CONTEXT_SUGGESTION = (
    "FlowForm has focused repository documentation available through the "
    "flowform-doc-context skill and flowform-docs tools. For non-trivial work "
    "where existing behaviour or project boundaries matter, consider loading "
    "that context once now. Do not reload it on later prompts unless the task "
    "scope materially changes or the user asks for another documentation check."
)


def main() -> int:
    data = read_hook_input()
    session_id = resolve_session_id(data)
    if not session_id:
        return 0

    state = load_state(session_id)
    should_suggest = not state.get("doc_context_suggested")
    if should_suggest:
        state["doc_context_suggested"] = True
    save_state(session_id, state)
    if should_suggest:
        print(DOC_CONTEXT_SUGGESTION)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
