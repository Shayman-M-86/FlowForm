# How to Run an Implementation Session

## Starting a session

Run `/impl-start` at the top of every session. This executes
`backend/scripts/impl-session-start.sh` and prints everything needed in one block:

1. README and operating rules
2. Flow matrix
3. Latest pass report (your current state)
4. Next target file (auto-detected from pass reports)
5. Next target prompt (stop conditions and scope constraints)

Read the output. Do not search for additional files — everything needed to begin
is already there.

## Working a pass

Follow the work loop in `agent-operating-rules.md`:

1. Build a context pack from the target in front of you
2. Write a local plan (chat only — never written to disk)
3. Implement only that plan
4. Add focused tests
5. Validate with `bash backend/scripts/run-tests.sh --ai -k "<filter>"`
6. Update stale docstrings in touched files only
7. Read `pass-template.md`, write the report to `pass-reports/<number>-<slug>.md`

## Moving to the next pass

The report is the signal that a pass is done. The next `/impl-start` will
auto-detect the new latest report and deliver the next target automatically.

No manual file selection needed between sessions.

## If something goes wrong mid-pass

Stop. Do not continue implementing. Write a local plan revision in chat and ask
for direction if the hard-stop rules in `agent-operating-rules.md` apply.
