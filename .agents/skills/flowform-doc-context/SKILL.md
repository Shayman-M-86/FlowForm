---
name: flowform-doc-context
description: Research how FlowForm works through a fresh isolated Codex process with focused documentation and implementation evidence, or find context for explicit documentation work. Use when the user asks how established FlowForm behaviour is implemented, an agent needs a compact factual briefing without adding retrieval history to its own context, documentation is explicitly in scope, or implementation inspection reveals a material documentation gap.
---

# FlowForm documentation context

Use this skill for answer-oriented FlowForm research, explicit documentation
work, or a material gap discovered while inspecting implementation. Do not
invoke it automatically for ordinary implementation tasks.

## Workflow

1. For a "how does this work?" question or implementation-grounding request,
   call the `flowform-research` MCP `research` tool. Pass the exact question and
   an optional repository-relative scope. Use `quick` depth by default and
   `thorough` only for ambiguous or cross-boundary questions.
2. For one simple lookup, or when delegation is unavailable, use the
   `flowform-docs` MCP `find` and `read` tools directly. Run
   `tools/docs/bin/docsys find --help` only when CLI search controls are needed.
3. Use `find` with concise terms, a documentation scope, or exact code files;
   keep the result set at three or fewer.
4. Use `read` for one selected path or section. Do not load neighbours or full
   documents by default. Preserve returned source line bounds in citations.
5. Treat implementation, tests, configuration, and automation as authoritative
   when changing behaviour or when a selected document is unreliable.
6. Run `impact` once near completion only when documentation meaning may have
   changed. Update only affected authored pages and regenerate generated pages.

The research tool starts a new non-persistent Codex process with no prior
session, user config, memories, project instructions, shell, web, or subagents.
It exposes only bounded read-only documentation and repository retrieval tools.
Consume its structured evidence packet; do not ask it to edit files.

When a parent agent supplies document paths, use them directly and skip
discovery. Keep answer-oriented research separate from `docs-maintainer`, which
owns bounded documentation edits. Do not scan the documentation tree or reload
context on ordinary follow-up prompts.
