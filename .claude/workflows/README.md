# Claude Workflow Framework

A pattern for running multi-pass AI implementation sessions against a fixed
source of truth. Each workflow is self-contained: specs, working files, and
session scripts all live together.

---

## When to use this

Use a workflow when you have:

- A body of spec/policy docs that the AI must treat as ground truth
- Implementation work that can be broken into ordered, discrete passes
- A need to resume across multiple sessions without re-establishing context

---

## Directory layout

```
.claude/workflows/<workflow-name>/
├── README.md               ← this file (per-workflow version describes the project)
├── source/                 ← immutable specs — AI reads, never edits
│   └── (your docs here)
├── working/
│   ├── AGENT.md            ← AI operating rules, context-mode ban, hard stops
│   ├── OPERATOR.md         ← human guide: how to run sessions, move passes, recover
│   ├── state.md            ← current pass + status (human-editable or auto-incremented)
│   ├── pass-template.md    ← schema for pass reports
│   ├── targets/
│   │   ├── 01-<name>/
│   │   │   ├── spec.md     ← what this pass must achieve (written by human upfront)
│   │   │   └── prompt.md   ← exact AI boot prompt for this pass
│   │   └── 02-<name>/
│   │       ├── spec.md
│   │       └── prompt.md
│   └── pass-reports/       ← AI writes one report per completed pass
└── scripts/
    ├── session-start.sh    ← boot script: injects source docs + current prompt inline
    └── new-workflow.sh     ← (only in the framework root) scaffold a new workflow
```

---

## How source docs work

`source/` holds the ground truth the AI must implement against. These files
are **read-only for the AI** — it may never propose edits to them during a
session. If code and source disagree, the AI stops and flags it; the human
resolves it by updating source first, then resuming.

The session-start script reads `working/AGENT.md` to find the `SOURCE_DOCS`
list and cats each file inline into the boot context. The AI starts every
session already holding the full spec — no search, no fetch.

---

## How passes work

Each pass is a numbered directory under `working/targets/`. The number sets
the order. A pass has two files:

- `spec.md` — written by the human before the session. Describes what the
  pass must achieve, what is in scope, and what signals done.
- `prompt.md` — the exact text pasted to the AI as its first instruction
  after the session-start script runs.

`working/state.md` tracks the current pass number and whether it is
`in-progress` or `done`. The session-start script reads this to know which
target to load. When you confirm a pass is done, the script increments the
pass number automatically. You can also edit `state.md` manually to rerun
a pass or skip ahead.

---

## Context-mode ban

Policy docs and flow specs are load-bearing — every word matters. Context-mode
tools (ctx_execute, ctx_batch_execute, ctx_fetch_and_index) compress and
summarize, which silently drops constraints.

**Hard rule:** within a workflow session, the AI must use `Read` directly for
any file under `source/` or `working/`. Context-mode is banned for these
paths. This rule is restated in `working/AGENT.md` so it is in the AI's
boot context every session.

---

## Creating a new workflow

Run the scaffold script from the repo root:

```bash
bash .claude/workflows/scripts/new-workflow.sh
```

It will prompt for:

- Workflow name (used as the directory name, kebab-case)
- A one-line description
- Number of passes (creates numbered target directories)
- Pass names (one per pass)

Then follow the manual steps in `working/OPERATOR.md` inside the new workflow.

---

## Updating an existing workflow

- To add a pass: create a new `working/targets/<N>-<name>/` directory with
  `spec.md` and `prompt.md`. Update `state.md` if needed.
- To revise a spec mid-implementation: edit the file in `source/`, note the
  change in the current pass report under "Policy change during pass".
- To rerun a pass: set `current_pass` in `state.md` back to that number and
  set `status: in-progress`.
