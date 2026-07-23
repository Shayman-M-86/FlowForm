#!/usr/bin/env python3
"""Record a documentation-impact review so task completion can proceed.

The Stop hook asks for a documentation review when canonical docs may be
affected. An agent runs this command to record the outcome — which documents it
updated and/or which it left unchanged and why. Recording keys the review to the
current set of changed implementation files, so the next completion attempt
succeeds (and a later, different change requests a fresh review).

This never edits documentation. It only stores the agent's review decision.

Usage:
    python3 .claude/hooks/record_doc_review.py \\
        --updated "Responses and encryption" \\
        --unchanged "Submissions=Internal refactor preserved documented behaviour."

    # or supply the whole record as JSON on stdin / via --json:
    python3 .claude/hooks/record_doc_review.py --json '{"reviewed": true, ...}'

At least one of --updated / --unchanged / --json is required. The most recent
session with a pending review is used unless --session is given.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from docsys_hook_lib import (  # noqa: E402
    STATE_DIR,
    changed_files_since,
    fingerprint,
    load_state,
    save_state,
)


def _latest_session_with_pending() -> str | None:
    if not STATE_DIR.exists():
        return None
    candidates = []
    for p in STATE_DIR.glob("*.json"):
        try:
            data = json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if data.get("pending_review") or data.get("base_commit"):
            candidates.append((p.stat().st_mtime, p.stem))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="record_doc_review")
    parser.add_argument(
        "--updated",
        action="append",
        default=[],
        help="title of a document that was updated (repeatable)",
    )
    parser.add_argument(
        "--unchanged",
        action="append",
        default=[],
        help='"Title=reason" for a document left unchanged (repeatable)',
    )
    parser.add_argument("--json", help="full review record as a JSON object")
    parser.add_argument("--session", help="session id (default: latest pending)")
    args = parser.parse_args(argv)

    if not (args.updated or args.unchanged or args.json):
        parser.error("provide --updated, --unchanged, and/or --json")

    session_id = args.session or _latest_session_with_pending()
    if not session_id:
        print(
            "No session state found to attach the review to. Was a task in "
            "progress? Re-run inside the session, or pass --session.",
            file=sys.stderr,
        )
        return 1

    state = load_state(session_id)

    if args.json:
        try:
            record = json.loads(args.json)
        except json.JSONDecodeError as exc:
            print(f"--json is not valid JSON: {exc}", file=sys.stderr)
            return 1
    else:
        unchanged = {}
        for item in args.unchanged:
            title, _, reason = item.partition("=")
            unchanged[title.strip()] = reason.strip() or "no reason given"
        record = {
            "reviewed": True,
            "updated_documents": [t.strip() for t in args.updated],
            "unchanged_documents": unchanged,
        }

    # Fingerprint the CURRENT task-introduced implementation changes, matching
    # exactly what the Stop hook computes (base diff minus pre-existing dirty
    # files) so the recorded review unblocks the next completion attempt.
    base = state.get("base_commit")
    preexisting = set(state.get("preexisting_impl_files") or [])
    all_impl, _ = changed_files_since(base)
    impl_files = [f for f in all_impl if f not in preexisting]
    fp = fingerprint(impl_files)

    record["fingerprint"] = fp
    record["recorded_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    state["reviewed"] = record
    state.pop("pending_review", None)
    save_state(session_id, state)

    updated = record.get("updated_documents") or []
    unchanged = record.get("unchanged_documents") or {}
    print(
        f"Recorded documentation review for session {session_id}: "
        f"{len(updated)} updated, {len(unchanged)} unchanged. "
        "Completion will now proceed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
