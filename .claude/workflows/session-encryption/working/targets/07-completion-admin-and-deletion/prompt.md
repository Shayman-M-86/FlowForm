# Pass 07: Completion, Admin Paths, and Deletion

Read `.claude/workflows/session-encryption/working/targets/07-completion-admin-and-deletion/spec.md` in full before writing any code.

Dependency check: confirm `.claude/workflows/session-encryption/working/pass-reports/06-integration-tests-session-and-answers.md` exists and is signed off. If not, stop.

New file: `backend/app/services/public_submissions/core/completion.py`.
Existing file to extend: `backend/app/services/results.py` — read it fully before editing.

Pass-specific constraints:
- Deletion ordering is non-negotiable: response DB first, then core (doc 06)
- Completion idempotency: SELECT before any lock; if already completed return stored state immediately
- Admin paths must go through explicit authorization — never query response tables from API handlers (doc 01)

{{context: context/code-conventions.md}}

{{context: context/logging-rules.md}}

{{context: context/validation-ladder.md}}

{{context: context/testing-patterns.md}}

After implementing, run: `bash backend/scripts/run-tests.sh --ai -k "completion or admin_decrypt or deletion"`

{{context: context/pass-report-template.md}}
