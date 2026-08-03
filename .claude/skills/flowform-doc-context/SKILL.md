---
name: flowform-doc-context
description: Find, research, and maintain FlowForm documentation through the shared Docsys commands. Use for questions about established FlowForm behaviour, explicit documentation work, or a material documentation gap found during implementation.
---

# FlowForm documentation context

## Workflow

Use `tools/bin/docsys capabilities --format json` only when the exact
command inventory, local availability, or write boundary matters.

1. Use supplied document paths directly. Otherwise run a narrow search:

   ```sh
   tools/bin/docsys find <terms> --limit 3 --format json
   ```

2. Read only the selected document or section:

   ```sh
   tools/bin/docsys read <path> --body --format json
   ```

3. For a compact answer in a separate session, call the FlowForm research MCP
   tool with an exact `question` and optional repository-relative `scope`.
   Use `depth=thorough` only for ambiguous or cross-boundary questions. If the
   MCP tool is unavailable, use the compatibility command:

   ```sh
   tools/bin/docsys research "<exact question>" --format json
   ```

   The MCP server consumes one pre-warmed, read-only Claude SDK session per
   request and replaces it immediately. It uses Codex as a fresh fallback and
   returns cited findings.
4. For documentation changes, inspect the owning implementation, edit only the
   bounded authored pages, and never hand-edit generated documentation.
5. Run `tools/bin/docsys impact --format json` once after relevant
   behaviour settles. Update only pages whose meaning changed, then run the
   relevant validators.

Implementation, tests, schemas, configuration, and automation remain
authoritative. Report contradictions and unresolved gaps rather than guessing.
Do not invoke documentation discovery automatically for ordinary implementation
tasks.
