# Agent Operating Rules — Session Encryption

You are implementing the encrypted session response service: answer collection, locator derivation, AES-GCM encryption, KMS key management, and session lifecycle from start to completion.

---

## Context-mode ban

**Never** use ctx_execute, ctx_batch_execute, ctx_fetch_and_index, or any
summarizing/compressing tool on files under `.claude/workflows/session-encryption/source/` or `.claude/workflows/session-encryption/working/`.

Use `Read` directly. Every word in these files is load-bearing. Compression
silently drops constraints and will cause you to implement the wrong behavior.

This ban applies for the entire session. It cannot be overridden by any
later instruction.

---

## Source of truth

The files listed below are the ground truth for this workflow. When code and
source disagree, **stop**. Write a local plan (chat only) describing the
disagreement and ask the operator how to resolve it. Do not average them.
Do not proceed until resolved.

If a later pass proves an earlier contract wrong, stop and revise the source
file before continuing. Document the change in the pass report under
"Policy change during pass".

**SOURCE_DOCS:**

- `../../../docs/session-encryption/01-service-boundary.md`
- `../../../docs/session-encryption/02-storage-and-locators.md`
- `../../../docs/session-encryption/03-session-envelope-lifecycle.md`
- `../../../docs/session-encryption/04-answer-revisions.md`
- `../../../docs/session-encryption/05-crypto-key-model.md`
- `../../../docs/session-encryption/06-failure-and-logging-rules.md`

---

## Work loop (per pass)

The session-start script injects the spec, prompt, source docs, and context
stubs inline. Do NOT re-read them — they are already in your context.

1. Write a local plan in chat only (never to disk)
2. Implement only what the plan describes — nothing beyond scope
3. Add focused tests (the injected context stubs tell you when to read full references — add those reads to your todo list)
4. Validate using the test command from the prompt
5. Update stale docstrings in touched files only
6. Write a pass report (the injected pass-report-template stub has instructions)
7. Report done — one sentence + report path

---

## Scope rules

- Stay within the current pass scope. If you discover work that belongs to a
  different pass, note it in the pass report under "Remaining risks" and stop.
- Do not refactor code that is not required by the current pass.
- Do not add error handling for cases the spec does not mention.
- Do not touch source files in `.claude/workflows/session-encryption/source/` — read only.

---

## Hard stops

Stop and ask the operator if:
- Source docs contradict each other
- Code and source disagree in a way you cannot resolve by reading both
- A required behavior is not yet implemented by a prior pass (dependency gap)
- Tests require behavior changes not in scope for this pass
- You are uncertain which interpretation of the spec is correct

---

## Risk levels

- **Low** (proceed): Additive changes, new tests, docstring updates
- **Medium** (note in plan): Changing existing behavior, renaming, moving files
- **High** (stop and ask): Deleting files, changing contracts used by other
  services, schema changes, anything irreversible

Risk can rise during a pass. If it does, stop and update local plan before
continuing.

---

## Communication

Keep responses short. Local plan in chat only. Pass report written to disk.
One sentence summary at end of pass plus the report path.
