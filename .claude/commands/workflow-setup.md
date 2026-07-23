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
   with paths relative to the workflow root. Workflows live at
   `.claude/workflows/<slug>/`, so docs under `docs/` require `../../../docs/your-doc.md`
   (three levels up: out of the slug dir, out of workflows/, out of .claude/).
   Always verify with `ls` before writing — wrong depth silently produces warnings at runtime.

2. Create `context/` and `source/` directories inside the new workflow.
   These form a **two-tier context system** that keeps prompts lean while
   giving the agent full detail on demand:

   - **`context/` — stubs** (injected automatically via `{{context:}}` tokens).
     Each stub is 5–8 lines: the key rules an agent must follow, plus a pointer
     to the full reference. Stubs are injected inline into the prompt by the
     session-start script, so they consume context window on every pass.
     Keep them short — rules only, no examples.

   - **`source/` — full references** (read on demand by the agent).
     Each full reference contains the complete detail: examples, fixture lists,
     factory imports, error class hierarchies, etc. The agent reads these with
     the Read tool only when it's about to write the relevant code (e.g. reads
     `source/testing-patterns-full.md` right before writing tests). Full
     references are never injected automatically — they stay out of context
     until needed.

   **Naming convention:** stub is `context/<topic>.md`, full reference is
   `source/<topic>-full.md`. Each stub must end with an explicit instruction
   to add a todo item before the relevant action:

   ```
   **Before <action>**, add a todo item:
   "Read `.claude/workflows/<slug>/source/<topic>-full.md` for <what it covers>."
   Do NOT skip this — the stub above is a summary, not the full specification.
   ```

   This ensures the agent schedules the full-reference read in its todo list
   rather than forgetting or skipping it.

   **Full paths:** all paths in stubs, source files, AGENT.md, and prompts must
   be written from the project root (`.claude/workflows/<slug>/...`), not
   relative to the workflow directory. The agent runs from the project root and
   uses `Read` with these paths directly. Use `{{WORKFLOW_SLUG}}` in template
   files — `new-workflow.sh` replaces it at scaffold time.

   **Always create these three pairs** (inspect the actual codebase first —
   never write from memory or generic advice):

   a. **testing-patterns** — Read `tests/conftest.py`,
      `tests/integration/*/conftest.py`, and the factories file.
      - Stub (`context/testing-patterns.md`): test runner command, `-k` filter
        rule, fixture names, factories import path. ~5 lines.
      - Full (`source/testing-patterns-full.md`): scope rules (unit vs
        integration vs e2e), DB fixture details and when to use each, factory
        helper usage with examples, response DB routing assertions, unit test
        style rules.

   b. **code-conventions** — Read existing services, repositories, and schemas.
      - Stub (`context/code-conventions.md`): layer boundaries (what calls
        what), error class to use, type hint rule, persistence helper names. ~6 lines.
      - Full (`source/code-conventions-full.md`): typing patterns with examples,
        error translation details, layer rules with import examples, persistence
        helpers (`flush_with_err_handle` vs `commit_with_err_handle`), module
        structure rules.

   c. **logging-rules** — Read existing logging calls and any logging config.
      - Stub (`context/logging-rules.md`): what must never be logged, safe
        fields list, Sentry rule. ~5 lines.
      - Full (`source/logging-rules-full.md`): complete safe/unsafe field
        lists, structured logging examples, error reporting patterns.

   d. **pass-report-template** — the structured format agents use to write
      pass reports at the end of each pass.
      - Stub (`context/pass-report-template.md`): remind the agent to write
        a pass report when done, mention the pass-forward section, and point
        to the full template. ~5 lines.
      - Full (`source/pass-report-template-full.md`): the complete report
        structure with all sections. Must include at minimum:
        **Changed files**, **Behavior implemented**, **Tests run** (exact
        command + result), **Trace notes** (route entry points, service
        methods, repository helpers, side effects, transaction boundaries,
        tests that now describe behavior), **Remaining risks**, and
        **Pass-forward**. Adapt section names to the workflow's domain but
        keep the same coverage.

      The **Pass-forward** section is critical: instruct the agent to find
      the next pass directory in `working/targets/` (one number higher), read
      that pass's `prompt.md`, and write only what the next agent needs from
      this pass — file paths created, contracts established, gotchas, decisions
      (3–8 bullets). The session-start script extracts only this section as
      carry-over context for the next pass. If the next agent needs more
      detail, it can Read the full report manually.

   e. **validation-ladder** — escalating validation levels matched to risk.
      - Stub (`context/validation-ladder.md`): the basic rule — "start with
        focused `-k` tests; climb the ladder as risk rises" — plus the
        ladder levels as a numbered list. ~6 lines.
      - Full (`source/validation-ladder-full.md`): each level with examples,
        useful test selectors for this workflow, and the rule: "skipped
        validation is not green — record it in the pass report." Derive the
        selectors from the test suite and spec scope. Typical levels:
        1. Unit tests for helpers and contracts
        2. Service tests for business logic decisions
        3. Integration tests for cross-layer behavior
        4. Route/API tests for endpoint contracts
        5. Broader backend validation after shared-domain changes

   Additional pairs as needed (e.g. `api-patterns` for passes that touch
   routes). Only create files you have actually inspected the code for.

   **Injection mechanics:** `{{context: context/<file>.md}}` tokens in
   `prompt.md` are replaced inline by the session-start script at the exact
   position they appear. If the referenced file is missing the script crashes
   with a clear error. Paths are relative to the workflow root. Source files
   are NOT injected — the stub tells the agent when and how to read them.

3. For each target, pre-fill `working/targets/<N>-<name>/spec.md` based on
   what you learned in Phase 1. Also fill in each `prompt.md` with:
   - the exact Read instruction for the spec
   - dependency checks (confirm prior pass files exist before proceeding)
   - pass-specific constraints (not generic advice — derived from spec + code)
   - context stub injections for **every implementation pass**:
     `{{context: context/code-conventions.md}}`
     `{{context: context/logging-rules.md}}`
     `{{context: context/validation-ladder.md}}`
     `{{context: context/testing-patterns.md}}`
     Place these four together, after the pass-specific instructions and
     before the final test command. Then after the test command, place:
     `{{context: context/pass-report-template.md}}`
     This ordering means the agent sees: rules → implement → test → report.
     For validation and human-action passes, omit the implementation context
     stubs (code-conventions, logging-rules, validation-ladder, testing-patterns)
     but still include `{{context: context/pass-report-template.md}}` at the
     end — every pass writes a report.
   - the exact test command to run at the end

   The stubs tell the agent the key rules upfront. When the agent is about to
   write implementation code, tests, or a pass report, it will follow the
   stub's pointer to read the corresponding `source/*-full.md` file on
   demand. You do NOT need to add explicit Read instructions for source files
   in the prompt — the stubs already contain the pointer.

4. Update `.claude/commands/impl-start.md` to point to the new workflow's
   session-start script. Read the file first, then replace the script path and
   description. The format must be:

   ```
   Run this at the start of a <Workflow Name> implementation session.

   ```bash
   bash .claude/workflows/<workflow-slug>/scripts/session-start.sh
   ```

   Run this with the Bash tool directly — do NOT use context-mode or ctx_batch_execute. The output is the context: agent rules, source docs, current pass spec, and prompt are all injected inline. Read the full output, then begin the current pass.

   ```

5. Print the setup checklist from the workflow's `README.md` with each item

   marked [done] or [todo].

Tell the user:
"Workflow scaffolded. Fill in any [todo] items above, then run /impl-start to begin."
