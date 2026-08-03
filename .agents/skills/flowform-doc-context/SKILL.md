---
name: flowform-doc-context
description: Find, research, and maintain FlowForm documentation through the shared Docsys commands. Use for questions about established FlowForm behaviour, explicit documentation work, or a material documentation gap found during implementation.
---

# FlowForm documentation context

## Workflow

1. Use supplied document paths directly. Otherwise run a narrow search:

   ```sh
   tools/docs/bin/docsys find <terms> --limit 3 --format json
   ```

2. Read only the selected document or section:

   ```sh
   tools/docs/bin/docsys read <path> --body --format json
   ```

3. For a compact answer in a separate session, run:

   ```sh
   tools/docs/bin/docsys research "<exact question>" --format json
   ```

   Use `--depth thorough` only for ambiguous or cross-boundary questions. The
   command starts a fresh, read-only Codex session and returns cited findings.
4. For documentation changes, inspect the owning implementation, edit only the
   bounded authored pages, and never hand-edit generated documentation.
5. Run `tools/docs/bin/docsys impact --format json` once after relevant
   behaviour settles. Update only pages whose meaning changed, then run the
   relevant validators.

Implementation, tests, schemas, configuration, and automation remain
authoritative. Report contradictions and unresolved gaps rather than guessing.
Do not invoke documentation discovery automatically for ordinary implementation
tasks.
