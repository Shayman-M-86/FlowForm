Run this at the start of a Session Encryption implementation session.

```bash
bash .claude/workflows/session-encryption/scripts/session-start.sh
```

Run this with the Bash tool directly — do NOT use context-mode or ctx_batch_execute. The output is the context: agent rules, source docs, current pass spec, and prompt are all injected inline. Read the full output, then begin the current pass.
