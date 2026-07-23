# Pass 04: Session Start

Read `.claude/workflows/session-encryption/working/targets/04-session-start/spec.md` in full before writing any code.

Dependency checks:

- Confirm `backend/app/crypto/kms.py` exists (pass 03). If not, stop.
- Confirm `backend/app/repositories/response/response_envelope_repo.py` exists (pass 02). If not, stop.

You are modifying `backend/app/services/public_submissions/core/session_starter.py`. Read it fully before editing.

Key constraint: the browser resume token must never be set or returned until both the core session and response envelope have committed. Any failure after core commits but before envelope commits must mark the core session abandoned — not silently swallowed.

{{context: context/code-conventions.md}}

{{context: context/logging-rules.md}}

{{context: context/validation-ladder.md}}

{{context: context/testing-patterns.md}}

After implementing, run: `bash backend/scripts/run-tests.sh --ai -k "session_start"`

{{context: context/pass-report-template.md}}
