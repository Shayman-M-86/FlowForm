---
name: flowform-doc-verification
description: Quickly promote FlowForm Project Knowledge documentation with Docsys. Use when the user asks to verify, approve, promote, or bulk-verify documentation before a commit; the request itself authorizes promotion.
---

# Verify FlowForm documentation

Run the promotion workflow promptly. Do not turn it into a review project.

## Workflow

1. Treat the user's request to verify or promote named files, folders, or an
   obvious current selection as approval. Do not ask for approval again.
2. Expand folders to authored Markdown under `docs/project-knowledge/`, excluding
   generated documentation. Development Workspace is never promoted.
3. Run the command immediately with all selected paths:

   ```sh
   PYTHONPATH=tools/docs python3 -m docsys evidence promote --staged \
     docs/project-knowledge/path.md
   ```

4. Report the updated paths and the `git add` command printed by Docsys. Do not
   stage them unless the user explicitly asks.
5. Report any command error without starting a broader audit. Let pre-commit
   perform the remaining read-only validation.

Do not inspect implementation, run tests, present an approval packet, or review
every claim unless the user explicitly asks. Do not stage, commit, or push
unless asked.
