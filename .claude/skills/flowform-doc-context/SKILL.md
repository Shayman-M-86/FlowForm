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
3. Use the returned implementation locations to inspect the relevant code,
   tests, configuration, schemas, CI, or infrastructure. Implementation
   evidence is authoritative.
4. After behavioural or architectural changes, call `get_impacted_docs`.
   Update only documents whose meaning actually changed.

Do not scan the full documentation tree.

## Reliability

- Surface Docsys reliability warnings before presenting affected claims as
  current.
- When the assessment is unreliable, say: **“I think the documentation is
  unreliable for this question.”**
- Report contradictions with repository evidence explicitly.
- If editing a contradicted page, correct it, set `status: draft`, and clear
  `verified_evidence_digest`.
- For explanation-only work, ask before expanding a focused check into a broad
  audit.

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
- Let pre-commit maintain `last_edited` and check evidence drift.
