---
name: flowform-doc-context
description: Find and read focused FlowForm documentation only when the user requests documentation work or implementation inspection reveals a material documentation gap.
---

# FlowForm documentation context

Use this skill only for explicit documentation consultation or editing,
documentation-focused tasks, or a material gap discovered while inspecting the
implementation. Do not invoke it automatically at task start.

## Workflow

1. Run `tools/docs/bin/docsys find --help` only when search controls are needed.
2. Use `find` with concise terms, a documentation scope, or exact code files;
   keep the result set at three or fewer.
3. Use `read` for one selected path or section. Do not load neighbours or full
   documents by default.
4. Treat implementation, tests, configuration, and automation as authoritative
   when changing behaviour or when a selected document is unreliable.
5. Run `impact` once near completion only when documentation meaning may have
   changed. Update only affected authored pages and regenerate generated pages.

When a parent agent supplies document paths, use them directly and skip
discovery. Do not scan the documentation tree or reload context on ordinary
follow-up prompts.
