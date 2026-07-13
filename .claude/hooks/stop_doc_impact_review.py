#!/usr/bin/env python3
"""Stop hook: request a documentation-impact review before finishing.

When the main agent tries to finish, this hook checks whether implementation
changes during the task may have affected canonical documentation. If so, it
asks for one review step; otherwise it allows completion immediately.

It reuses the existing ``docsys`` impact detection (via ``docsys_hook_lib``) and
never edits documentation itself. The review is a human/agent judgement: update
docs only when documented behaviour actually changed, or record why not.

Lifecycle
---------
1. Read ``session_id`` and ``stop_hook_active`` from stdin.
2. Compute implementation files changed since the task's base commit.
3. Documentation-only or trivial changes → allow (nothing to review).
4. If the agent already recorded a review for the current change fingerprint
   → allow (loop prevention).
5. Run docsys impact; collect high/medium-confidence canonical docs.
6. None affected → allow.
7. Some affected → block once with an actionable message and how to record the
   review.

Loop prevention
---------------
``stop_hook_active`` is respected as a hard stop: if it is true we never block
again. Independently, once a review record whose fingerprint matches the
current changed-file set exists, completion is allowed — so recording a review
(update list or no-update reasons) always lets the next Stop succeed.

Blocking uses the Stop-hook JSON contract: ``{"decision": "block", "reason":
...}``. The reason text is fed back to the agent.
"""
from __future__ import annotations

import json
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

REVIEW_CMD = "python3 .claude/hooks/record_doc_review.py"


def _allow() -> int:
    # Empty output + exit 0 = allow the stop.
    return 0


def _block(reason: str) -> int:
    """Signal a block understood by both Claude Code and Codex.

    Both agents read ``{"decision": "block", "reason": ...}`` from stdout (with
    exit 0) as "block the stop and feed the reason back to the agent". This is
    a drop-in shared contract, so no per-agent branching is needed.
    """
    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


def _format_reason(impacted: list[dict], fp: str) -> str:
    lines = ["Documentation impact review required.", "", "Likely affected:"]
    for d in impacted:
        lines.append(f"- {d['title']}  ({d['confidence']})")
    lines += [
        "",
        "Review these documents using the FlowForm Docsys MCP tools "
        "(get_document / get_related on the flowform-docs server). Update them "
        "only if the documented behaviour, responsibilities, boundaries, "
        "invariants, or workflow changed. Otherwise record why no update is "
        "needed.",
        "",
        "When done, record the review so completion can proceed, e.g.:",
        "",
        f"  {REVIEW_CMD} \\",
        '    --updated "Responses and encryption" \\',
        '    --unchanged "Submissions=Internal refactor preserved documented behaviour."',
        "",
        "Record at least one updated or unchanged document. This review is "
        "requested once; it will not block again after you record it.",
    ]
    return "\n".join(lines)


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

    # Record what we asked for so the review recorder can validate against it.
    state["pending_review"] = {
        "fingerprint": fp,
        "impacted": impacted,
        "changed_files": impl_files,
    }
    save_state(session_id, state)
    return _block(_format_reason(impacted, fp))


if __name__ == "__main__":
    raise SystemExit(main())
