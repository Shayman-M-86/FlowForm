Guide the user through setting up a new Claude implementation workflow.
This is a two-phase process: curate canonical docs first, then scaffold the workflow.
Do NOT use context-mode tools at any point during this command — use Read directly for all files.

---

## Phase 1 — Curate

Ask the user:
1. What are you implementing? (one paragraph, plain language)
2. Do relevant docs already exist in `docs/`? If yes, which ones?
3. What is the rough scope — how many distinct passes do you expect?

Then do the following:

**Audit existing docs (if any):**
Read each doc the user named using Read. For each, check:
- Is the behavior fully specified or are there gaps?
- Do any two docs contradict each other?
- Is there a clear "done" signal for each behavior described?

Report findings as a short list: [complete], [gap: <what's missing>], or [conflict: <what disagrees>].

**Draft missing docs:**
For any gaps, work with the user to write the missing content.
Write new docs to `docs/` using the same structure and tone as the existing ones.
Do not write to `docs/` without the user confirming the content first.

**Stabilize:**
When all source docs are gap-free and conflict-free, tell the user:
"Source docs look stable. Ready for readiness check."

---

## Phase 2 — Readiness check

Before scaffolding, verify all of the following. Report [pass] or [fail] per item:

- [ ] Every behavior the implementation must produce is described in at least one source doc
- [ ] No two source docs contradict each other on the same behavior
- [ ] The scope can be broken into discrete ordered passes (each pass has a clear entry point and done signal)
- [ ] There is a way to validate each pass (integration tests, endpoint behavior, etc.)
- [ ] The source docs are in `docs/` and will not move during implementation

If any item fails: stay in Phase 1, fix the issue, re-check.

If all pass: tell the user the check passed and ask:
"Ready to scaffold the workflow. I'll run new-workflow.sh — do you want to name the passes now or fill them in manually after?"

---

## Phase 3 — Scaffold

Run the scaffold script interactively:

```bash
bash .claude/workflows/scripts/new-workflow.sh
```

Run with the Bash tool directly.

After scaffolding, do the following automatically:

1. Update `working/AGENT.md` in the new workflow — fill in the `SOURCE_DOCS` list
   with paths relative to the workflow root (e.g. `../../docs/your-doc.md`).
   Use Read on each source doc to confirm the path resolves correctly.

2. For each target, pre-fill `working/targets/<N>-<name>/spec.md` based on
   what you learned in Phase 1. Leave `prompt.md` as the template default —
   the user can refine it before running sessions.

3. Print the setup checklist from the workflow's `README.md` with each item
   marked [done] or [todo].

Tell the user:
"Workflow scaffolded. Fill in any [todo] items above, then run:
bash .claude/workflows/<workflow-slug>/scripts/session-start.sh"
