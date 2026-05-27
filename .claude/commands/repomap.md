---
description: Refresh the repo map using parallel subagents - one per group in .claude/repomap-config.json
allowed-tools: mcp__flowform-repomap__start_session, mcp__flowform-repomap__save_summary, mcp__flowform-repomap__build_map, mcp__flowform-repomap__import_from_repomap_md, Agent, Read, Bash
---

Refresh the FlowForm repo map using parallel subagents. Each agent handles a
group of related paths from the `agents` array in `.claude/repomap-config.json`.

## Steps

1. Read `.claude/repomap-config.json` to get the `agents` groups and `output_dir`.

2. Call `start_session()`.

3. Spawn all agents **in parallel** using the Agent tool — one per group.
   Each agent receives this exact prompt (substitute the real paths):

   > You are summarising a group of related directories in the FlowForm repo.
   > For each path listed below, do the following:
   > - Run `ls <full_path>` to see the contents.
   > - Read 2-3 representative files that reveal purpose (e.g. a service, model,
   >   route handler, or component). Skip `__pycache__`, lock files, and generated files.
   > - Write a 2-4 sentence summary: purpose, key contents, notable patterns.
   >
   > Paths to summarise:
   > - backend/app/domain/
   > - backend/app/schema/
   > - (etc — list the actual paths for this agent's group)
   >
   > Return your results as a JSON array, one object per path:
   > [{"path": "backend/app/domain/", "summary": "..."}, ...]
   > Return ONLY the JSON array, no other text.

4. Collect all JSON arrays returned by the agents. For each `{path, summary}`
   object across all results, call `save_summary(path, summary)`.

5. Call `build_map()`.

6. Report: agent groups run, total paths summarised, rule files written.

## Summarisation guidelines (pass these to agents in their prompt)

- Base the summary on file contents actually read, not just filenames.
- Mention specific files, classes, or patterns that orient a developer.
- Skip generated files, lock files, and `__pycache__`.
- 2-4 sentences: purpose, key contents, notable patterns.

## Shortcut - import from existing repomap.md

If `repomap.md` already exists and you just want to split it into rule files
(e.g. after a server restart), call `import_from_repomap_md()` instead of
running the full parallel flow.
