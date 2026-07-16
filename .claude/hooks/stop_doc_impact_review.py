#!/usr/bin/env python3
"""Stop hook: warn about possible documentation impact before finishing.

When the main agent tries to finish, this hook checks whether implementation
changes during the task may have affected canonical documentation. If a
high-confidence (exact-file) match exists, it prints a short one-line heads-up
and allows completion. It never blocks and never edits documentation — updating
docs stays a human/agent judgement call.

Lifecycle
---------
1. Read ``session_id`` and ``stop_hook_active`` from stdin.
2. Compute implementation files changed since the task's base commit.
3. Documentation-only or trivial changes → allow silently.
4. If we already warned for the current change fingerprint → allow silently.
5. Run docsys impact; collect high-confidence canonical docs.
6. None affected → allow silently.
7. Some affected → print a one-line warning to stderr and allow.

The hook always exits 0 with empty stdout, so completion is never gated; the
notice goes to stderr purely as a heads-up.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from docsys_hook_lib import (  # noqa: E402
    changed_files_since,
    detect_impacted_docs,
    fingerprint,
    load_state,
    read_hook_input,
    resolve_session_id,
    save_state,
)


def _allow() -> int:
    # Empty stdout + exit 0 = allow the stop.
    return 0


def _warn(message: str) -> int:
    """Surface a non-blocking notice and allow completion.

    Printing to stderr with exit 0 shows the message to the user without
    feeding a "blocked" decision back to the agent, so the task finishes
    normally. This is a heads-up, not a gate.
    """
    print(message, file=sys.stderr)
    return 0


def _format_reason(impacted: list[dict]) -> str:
    titles = ", ".join(d["title"] for d in impacted)
    return (
        "docs may be affected by this change: "
        f"{titles}. Review and update only if documented behaviour changed."
    )


def main() -> int:
    data = read_hook_input()
    session_id = resolve_session_id(data)
    # Hard loop guard: if we are already inside a Stop-hook continuation, never
    # block a second time.
    if data.get("stop_hook_active"):
        return _allow()

    state = load_state(session_id)
    base = state.get("base_commit")
    preexisting = set(state.get("preexisting_impl_files") or [])

    all_impl, _doc_files = changed_files_since(base)
    # Only review files that changed DURING this task, not files that were
    # already dirty when the task started.
    impl_files = [f for f in all_impl if f not in preexisting]
    if not impl_files:
        # Documentation-only, no relevant change, or only pre-existing dirty
        # files: nothing this task needs to review.
        return _allow()

    fp = fingerprint(impl_files)

    # Loop prevention / already-reviewed: a recorded review matching the current
    # change set unblocks completion.
    reviewed = state.get("reviewed") or {}
    if reviewed.get("fingerprint") == fp:
        return _allow()

    impacted = detect_impacted_docs(impl_files)
    if not impacted:
        # Relevant code changed but no canonical doc is implicated: allow, and
        # remember so we do not recompute needlessly on repeated stop attempts.
        state["reviewed"] = {"fingerprint": fp, "auto": "no canonical docs impacted"}
        save_state(session_id, state)
        return _allow()

    # Remember that we warned for this change set so repeated stop attempts do
    # not recompute or repeat the notice.
    state["reviewed"] = {"fingerprint": fp, "warned": [d["title"] for d in impacted]}
    save_state(session_id, state)
    return _warn(_format_reason(impacted))


if __name__ == "__main__":
    raise SystemExit(main())
