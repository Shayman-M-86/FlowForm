# Operator Guide — Session Encryption

Human-facing instructions for running sessions, moving passes, and recovering
from problems. The AI never reads this file.

---

## Before you start

1. Populate `source/` with your spec and policy docs.
2. Fill in `working/targets/01-<name>/spec.md` for the first pass you plan
   to run. You can write them all upfront or one at a time.
3. Fill in `working/targets/01-<name>/prompt.md` — the exact first message
   you want the AI to receive for that pass (after the boot context).
4. Edit `working/state.md` to set `current_pass: 1` and `status: in-progress`.
5. Confirm `working/AGENT.md` has the correct `SOURCE_DOCS` list (paths
   relative to the workflow root).

---

## Starting a session

Run the session-start script from the repo root:

```bash
bash .claude/workflows/session-encryption/scripts/session-start.sh
```

Run this with the Bash tool directly — **not** via context-mode or
ctx_batch_execute. The output is the context: source docs, agent rules, and
the current pass prompt are all printed inline. Read the output, then begin.

---

## Working a pass

The AI follows the work loop in `AGENT.md`. Your role during a pass:

- Answer hard-stop questions promptly — the AI will wait
- Do not steer the AI toward out-of-scope changes mid-pass
- If the AI discovers a source disagreement, resolve it by editing the
  relevant file in `source/` first, then tell the AI to continue

When the AI writes a pass report to `working/pass-reports/`, review it before
moving on.

---

## Completing a pass

When you are satisfied with the pass report:

Run the session-start script again. It will detect that the current pass
report exists, mark the pass done, increment `state.md` to the next pass,
and print the next target's context.

Or edit `state.md` manually:
```
current_pass: 2
status: in-progress
```

---

## Rerunning a pass

Edit `state.md` to set `current_pass` back to the pass number and
`status: in-progress`. The existing report is not deleted — the new run will
overwrite it when the AI writes the new report.

---

## Adding a pass mid-workflow

1. Create `working/targets/<N>-<name>/spec.md` and `prompt.md`
2. Renumber subsequent targets if needed (and update `state.md` accordingly)

---

## Recovery: source disagreement found mid-pass

1. Tell the AI to stop (it should have stopped itself)
2. Edit the relevant `source/` file to resolve the disagreement
3. Note the change in the pass report under "Policy change during pass"
4. Tell the AI to reread the updated source file using `Read` and continue

---

## Recovery: wrong behavior implemented

1. Do not mark the pass done
2. Start a new session — the session-start script will reload the same pass
3. The AI will see the incomplete pass report (if it was written) and can
   use it as context for what went wrong

---

## Files the AI writes

- `working/pass-reports/<N>-<slug>.md` — one per completed pass
- Nothing else. The AI must not edit `source/`, `state.md`, `AGENT.md`,
  `OPERATOR.md`, or `targets/`.
