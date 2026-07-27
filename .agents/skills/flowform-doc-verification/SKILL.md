---
name: flowform-doc-verification
description: Lightly review and promote selected FlowForm Project Knowledge documents with user approval. Use when the user asks to verify, approve, or promote documentation before a commit.
---

# Verify FlowForm documentation

Keep verification short and proportional. It is a plausibility check, not a
full audit.

## Boundaries

- Verify only authored files under `docs/project-knowledge/`.
- Never promote Development Workspace or generated documentation.
- Do not change implementation code, commit, or push unless asked.

## Workflow

1. Use the paths the user provides. If none were provided, offer a short list
   from Docsys and let the user choose.
2. Read each selected page and sample the most obvious declared evidence.
   Check only its central claims. Run a focused command only when it would
   resolve a real doubt; do not require broad tests or exhaustive tracing.
3. Briefly report:
   - the selected paths and current status;
   - what evidence was sampled;
   - any material contradiction or uncertainty;
   - whether each page appears ready.
4. Ask the user to approve promotion. A concise summary is enough; show the
   full document or diff only when requested or when a correction needs review.
5. After approval, stage any selected edits and promote the exact paths:

   ```sh
   PYTHONPATH=tools/docs python3 -m docsys evidence promote --staged \
     docs/project-knowledge/path.md
   ```

6. Report what was promoted. Let the normal pre-commit workflow perform the
   commit-wide validation.

If an obvious material conflict is found, keep the page `draft`, clear its
digest, explain the conflict, and ask before widening the investigation.
