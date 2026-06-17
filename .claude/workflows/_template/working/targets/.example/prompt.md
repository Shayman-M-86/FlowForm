Read `.claude/workflows/{{WORKFLOW_SLUG}}/working/targets/<NN>-<name>/spec.md` in full before writing any code.

<Dependency check, e.g.: "Confirm `backend/app/crypto/` exists (pass 01). If not, stop.">
<Or: "No upstream dependencies — proceed immediately.">

All new files go under `<target directory>`.

<Pass-specific constraints — not generic advice. Derived from the spec and
actual codebase inspection. E.g.: "Handle the unique constraint race in
get_or_create — catch IntegrityError and re-fetch rather than crashing.">

{{context: context/code-conventions.md}}

{{context: context/logging-rules.md}}

{{context: context/validation-ladder.md}}

{{context: context/testing-patterns.md}}

After implementing, run: `<exact test command from spec>`

{{context: context/pass-report-template.md}}
