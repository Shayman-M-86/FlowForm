# Pass Report Template — Full Reference

Copy this structure into `.claude/workflows/session-encryption/working/pass-reports/<N>-<slug>.md` and fill in every section.

```md
## Pass report

Pass: <number> — <name>

Changed files:
* ...

Behavior implemented:
* ...

Tests run:
* `<exact command>` — <N> passed

Failures or skipped validation:
* ...

Policy change during pass:
* (note any source doc edits made to resolve disagreements, or "none")

Trace notes:
* entry points touched:
* service methods touched:
* repository helpers touched:
* side effects changed:
* transaction boundary changed or unchanged:
* tests that now describe behavior:

Remaining risks:
* ...

## Pass-forward

<Before writing this section, find the next pass directory in
`.claude/workflows/session-encryption/working/targets/` — it is the directory
whose number is one higher than this pass (e.g. if this is pass 02, look for
`.claude/workflows/session-encryption/working/targets/03-*/prompt.md`).
Read that prompt.md to understand what the next agent is working on.
Then write only the information that agent will need from this pass —
file paths created, contracts established, gotchas discovered, decisions
made that affect downstream work. 3–8 bullet points max.
If this is the final pass, write "n/a".>

* ...
```

Rules:

- Every section must be filled — use "none" if nothing applies.
- "Tests run" must include the exact command and pass count.
- "Failures or skipped validation" — skipped validation is not green. Record what was skipped and why.
- "Trace notes" — list concrete names (functions, files), not descriptions.
- "Remaining risks" — anything discovered during the pass that belongs to a later pass or needs operator attention.
- "Pass-forward" — read the next pass's `prompt.md` before writing this section.
  Only include what the next agent needs. The session-start script injects only
  this section as carry-over context. If the next agent needs more detail, it
  can read the full report manually.
