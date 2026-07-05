# Agent Operating Rules — {{WORKFLOW_NAME}}

You are implementing {{WORKFLOW_DESCRIPTION}}.

---

## Context-mode ban

**Never** use ctx_execute, ctx_batch_execute, ctx_fetch_and_index, or any
summarizing/compressing tool on files under `.claude/workflows/{{WORKFLOW_SLUG}}/source/` or `.claude/workflows/{{WORKFLOW_SLUG}}/working/`.

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
{{SOURCE_DOCS_LIST}}

---

## Work loop (per pass)

1. Read the current target `spec.md` in full using `Read`
2. Read the current target `prompt.md` in full using `Read`
3. Read all `SOURCE_DOCS` listed above using `Read` (already injected by
   session-start script — do not re-fetch)
4. Write a local plan in chat only (never to disk)
5. Implement only what the plan describes — nothing beyond scope
6. Add focused tests
7. Validate: run the test command from the spec
8. Update stale docstrings in touched files only
9. Write a pass report to `.claude/workflows/{{WORKFLOW_SLUG}}/working/pass-reports/<N>-<slug>.md` — read
   `.claude/workflows/{{WORKFLOW_SLUG}}/source/pass-report-template-full.md` for the template structure
10. Report done — one sentence + report path

---

## Scope rules

- Stay within the current pass scope. If you discover work that belongs to a
  different pass, note it in the pass report under "Remaining risks" and stop.
- Do not refactor code that is not required by the current pass.
- Do not add error handling for cases the spec does not mention.
- Do not touch source files in `.claude/workflows/{{WORKFLOW_SLUG}}/source/` — read only.

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
