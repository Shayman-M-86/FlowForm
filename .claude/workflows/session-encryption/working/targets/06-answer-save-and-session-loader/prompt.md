# Pass 06: Answer Save and Session Loader

Read `.claude/workflows/session-encryption/working/targets/06-answer-save-and-session-loader/spec.md` in full before writing any code.

Dependency check: confirm `.claude/workflows/session-encryption/working/pass-reports/05-session-start-contract-and-reconciliation.md` exists. If not, stop.

New files go in `backend/app/services/public_submissions/core/`.

Pass-specific constraints:
- Answer save has exactly 12 steps — implement in order, do not skip or reorder
- Mutation ID check at step 2 must happen before any row lock is taken
- Analytics event at steps 11–12 is secondary: if it fails after step 10 commits, log the failure and return success
- Session loader must return a safe context object — never expose internal IDs, locators, or key material to the caller

{{context: context/code-conventions.md}}

{{context: context/logging-rules.md}}

{{context: context/validation-ladder.md}}

{{context: context/testing-patterns.md}}

After implementing, run: `bash backend/scripts/run-tests.sh --ai -k "answer_save or session_loader"`

{{context: context/pass-report-template.md}}
