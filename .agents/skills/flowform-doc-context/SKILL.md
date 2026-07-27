---
name: flowform-doc-context
description: Load focused FlowForm documentation with Docsys for implementation, planning, architecture, repository questions, or documentation updates where existing behaviour and project boundaries matter.
---

# FlowForm documentation context

Use Docsys to load only the documentation needed for the task. Skip this for
spelling, formatting, and isolated mechanical changes.

## Workflow

1. Call `get_task_context` with the task and known changed files.
2. Check `documentation_reliability`, then read the returned primary documents.
   Load related pages only when a material gap remains.
3. For explanation-only questions, answer directly from verified, current
   primary documents when they cover the question. Do not inspect code merely
   because implementation locations were returned.
4. After behavioural or architectural changes, call `get_impacted_docs`.
   Update only documents whose meaning actually changed.

Do not scan the full documentation tree.

## Reliability

- Apply reliability to the documents actually used. A draft candidate or
  neighbour does not weaken a separate verified document.
- Surface a reliability warning only when the answer relies on an affected
  draft, stale, scaffold, or modified document.
- When the assessment is unreliable, say: **“I think the documentation is
  unreliable for this question.”**
- Report contradictions with repository evidence explicitly.
- If editing a contradicted page, correct it, set `status: draft`, and clear
  `verified_evidence_digest`.
- For explanation-only work, ask before expanding a focused check into a broad
  audit.

Inspect implementation only when changing or diagnosing it, when the user asks
for verification, or when the relevant documentation is missing, unreliable,
ambiguous, or internally contradictory.

## Documentation changes

- Put accepted current behaviour in Project Knowledge and unfinished work in
  the Development Workspace.
- Keep folder heads useful as overviews, update links and metadata with content,
  and change generators instead of generated files.
- Preserve globally unique titles and the
  `<folder-name>/<folder-name>-index.md` convention.
- Run relevant documentation validation. Do not commit unless explicitly asked.

## Verification

- Keep changed or contradicted Project Knowledge as `draft` with a null
  evidence digest until reviewed.
- Use `$flowform-doc-verification` when the user wants to review and promote
  Project Knowledge. That workflow handles approval and staged verification
  metadata.
- Let pre-commit check `last_edited` and evidence drift without changing files.
