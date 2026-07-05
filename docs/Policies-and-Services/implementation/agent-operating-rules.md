# Agent Operating Rules

## Work Loop

1. Build context pack from the target already in front of you.
2. Write local plan — compare docs to code, list gaps.
3. Implement ONLY that plan.
4. Add or update focused tests.
5. VALIDATE: `bash backend/scripts/run-tests.sh --ai -k "<filter>"`. Fix failures before continuing.
6. Update stale docstrings in touched files only.
7. Read `implementation/pass-template.md`, then write the report to `pass-reports/<target-number>-<target-slug>.md`. REPORT ONLY — no local plan in the file.
8. Stop or move to next target.

## Reading Rules

* Always read policy docs, target files, and code files directly with the Read tool — never via context-mode.
* Use context-mode only for codebase inspection: searching for callers, scanning large outputs, or grepping across files.
* Never use context-mode search to discover implementation scope — that comes from the target file.

## Scope Rules

* One pass = one service boundary, result contract, route contract, repository helper group, or test group.
* Do not edit files outside the pass unless direct compiler or test failure requires it.
* Do not implement all flows at once.
* Do not pre-design every branch before starting.
* Do not let services infer policy from incidental ORM shape when docs name a policy concept explicitly.

## Architecture Rules

* Keep access validation separate from subject resolution.
* Keep token lookup separate from final subject authority.
* Keep token issue/rotation separate from lookup.
* Keep transaction boundaries visible in orchestration.
* Update docs only when intended behavior changes, not to hide missing code.

## Risk Levels

| Risk | Examples | Rule |
| --- | --- | --- |
| Low | comments, docstrings, type hints, local result-object naming | agent can edit directly inside pass |
| Medium | service contracts, focused repository helpers, tests | local plan required before edits |
| High | auth checks, token rotation, canonical subject merge, session transaction boundary | explicit local plan plus broader validation required |
| Critical | data loss risk, auth bypass risk, destructive migration, irreversible token invalidation | human review before commit or irreversible action |

Risk can rise during a pass. If it does, stop and update local plan before continuing.

## Hard Stop Rules

Stop and ask for direction, or write a new local plan, when:

* pass needs second service boundary redesign before first makes sense
* docs and database schema disagree
* pass touches auth, token rotation, canonical merge, or transaction logic not named in local plan
* focused tests fail for unrelated reasons
* change would delete data, invalidate existing tokens, weaken auth checks, or require migration
* pass cannot keep codebase coherent without broader redesign

## Communication

Use `caveman` skill for implementation explanation, trace notes, and pass reports unless user disables it.
