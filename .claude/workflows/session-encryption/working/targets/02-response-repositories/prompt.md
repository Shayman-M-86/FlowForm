# Pass 02: Response Repositories

Read `.claude/workflows/session-encryption/working/targets/02-response-repositories/spec.md` in full before writing any code.

Dependency check: confirm `backend/app/crypto/` exists (pass 01). If not, stop.

All new files go under `backend/app/repositories/response/`.

Pass-specific constraint: handle the unique `answer_locator` constraint race in `get_or_create` — catch `IntegrityError` and re-fetch rather than crashing.

{{context: context/code-conventions.md}}

{{context: context/logging-rules.md}}

{{context: context/validation-ladder.md}}

{{context: context/testing-patterns.md}}

After implementing, run: `bash backend/scripts/run-tests.sh --ai -k "response_repo"`

{{context: context/pass-report-template.md}}
