Run a workflow audit of the implementation system — checks structural health, not content.

```bash
bash backend/scripts/impl-audit.sh
```

Run this with the Bash tool directly — do NOT use context-mode. Read the output and summarize:
- which targets are missing reports
- any reports with incomplete sections
- any broken file references in the session-start script
- any missing agent prompts

Give a short prioritized list of what to fix, not a line-by-line echo of the output.
