---
name: flowform-doc-verification
description: Promote and stage selected FlowForm Project Knowledge only when the user explicitly asks to approve, promote, or stage those documents.
---

# Verify FlowForm documentation

This skill records an explicit promotion decision. A generic request to verify
documentation means semantic review and does not authorize promotion or staging.

## Workflow

1. Treat an explicit request to approve, promote, or stage named files, folders,
   or an obvious current selection as authorization. Do not ask again.
2. Expand folders to authored Markdown under `docs/project-knowledge/`, excluding
   generated documentation. Development Workspace is never promoted.
3. Run the command immediately with all selected paths:

   ```sh
   tools/docs/bin/docsys evidence promote --staged --stage \
     docs/project-knowledge/path.md
   ```

4. Report the paths that Docsys updated and staged.
5. Report any command error without starting a broader audit. Let pre-commit
   perform the remaining read-only validation.

Stage only the selected documentation paths through Docsys. Do not commit,
push, stage other paths, or broaden this into a review unless asked.
