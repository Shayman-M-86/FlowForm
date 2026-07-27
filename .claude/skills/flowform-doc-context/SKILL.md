---
name: flowform-doc-context
description: Load focused FlowForm documentation through the Docsys MCP server and verify it against repository evidence. Use for non-trivial implementation, planning, architecture, repository questions, or documentation updates where existing FlowForm behaviour, boundaries, workflows, or domain rules matter.
---

# FlowForm documentation context

Use Docsys to retrieve the smallest relevant context. Do not scan the whole
documentation tree.

## Select the documentation root

- Use `docs`: it is the active documentation root.
- Use `old-docs` only as explicitly requested
  historical input. Never treat historical claims as current without verifying
  them against implementation evidence.
- Pass the same `docs_root` to every Docsys tool in one task.

Docsys selects `docs` when `docs_root` is omitted. Pass it explicitly when the
evidence boundary should be visible.

## Work with implementation context

1. Turn the request into a concise query naming the relevant concepts or
   domains.
2. Call `get_task_context` with `task`, known `changed_files`, and `docs_root`.
   Read `documentation_reliability` before using the returned pages.
3. Read the returned primary documents with `get_document`.
4. Read neighbouring documents only when the primary documents leave a
   material gap.
5. Use returned implementation locations to target code, tests, schemas,
   configuration, CI, or infrastructure inspection.
6. Treat implementation evidence as authoritative. Report contradictions
   instead of silently choosing documentation or code.
7. Make the requested plan or change.
8. After behavioural or architectural changes, call `get_impacted_docs` with
   the same `docs_root`. Review high- and medium-confidence results, updating
   only documents whose behaviour, responsibilities, boundaries, invariants, or
   workflows changed.

Skip retrieval for spelling, formatting, and isolated mechanical renames.

## Disclose reliability and control exploration

For an explanation or documentation-reading request, give the smallest useful
document-based explanation first. Treat it as provisional when Docsys says so.
Use an initial budget of 5–10 files and 2–3 focused searches, then synthesize
before expanding.

- If `documentation_reliability.requires_disclosure` is true, surface its
  message and reasons before presenting affected claims as current.
- Say exactly **“I think the documentation is unreliable for this question.”**
  when the assessment is `unreliable`, then identify the affected documents and
  why. A draft or missing verification baseline alone is provisional; do not
  call it a contradiction without implementation evidence.
- For explanation-only work, ask before widening the task into a broad audit
  once the initial budget is exhausted. Continue without asking when the user
  already requested verification, diagnosis, or implementation and the extra
  evidence is necessary to complete it.
- When implementation evidence contradicts a document, report the document
  claim and the conflicting repository evidence explicitly. If documentation
  editing is in scope, correct the claim, set `status: draft`, and clear
  `verified_evidence_digest` until the revised page is checked against staged
  implementation evidence.
  In read-only work, report that metadata update as required instead of editing.
- Never silently preserve `status: verified` after finding a material
  contradiction.

## Use and maintain documentation

1. Use retrieved documents to understand established terminology, ownership
   boundaries, invariants, and known workflows before inspecting the linked
   implementation evidence.
2. For a documentation change, read the target page, its structural parent,
   and only the neighbours needed to understand its boundary.
3. Put accepted current behaviour in Project Knowledge. Put proposals,
   investigations, decisions, plans, and unresolved work in the Development
   Workspace.
4. Verify every changed current-state claim against code, tests, schemas,
   configuration, CI, infrastructure, or reproducible generated output.
5. Preserve globally unique titles and the
   `<folder-name>/<folder-name>-index.md` naming convention.
6. Keep folder heads useful on their own: explain the subject, boundaries,
   lifecycle, and interaction of child categories. Links provide depth; they
   are not the substance of the page.
7. Do not create empty branches or taxonomy-only scaffolds. Change generators
   instead of hand-editing generated documentation.
8. Update front matter, code linkage, cross-links, and affected navigation with
   the content change. Keep status and `verified_evidence_digest` honest.
9. Run the relevant Docsys validation profile, link and metadata checks, and
   documentation-tool tests before reporting completion.
10. Do not commit independently unless the user explicitly asks.

## Verify a documentation update

Verification is a semantic review followed by deterministic automation:

1. Check the document's current-state claims against its declared
   implementation evidence.
2. Stage the implementation and documentation changes that belong in one
   commit.
3. Promote each reviewed document with
   `PYTHONPATH=scripts/docs python3 -m docsys evidence promote --staged
   docs/path.md`. Docsys writes the staged evidence digest and re-stages the
   document; do not calculate or paste a digest manually.
4. Let the Git pre-commit hook compare verified pages with the exact staged
   blobs and run the `commit` validation profile. If it stages an automatic
   downgrade to `draft`, review that page and either update and promote it or
   commit the honest draft state.

This permits implementation, documentation, and verification metadata to land
in one commit. The hook validates deterministic evidence; it does not replace
the semantic review required before promotion.

## Supporting tools

- `search_docs`: locate likely documents.
- `get_document` and `get_related`: retrieve one document or its graph
  neighbours.
- `check_freshness`: classify verification drift.
- `documentation_debt`: inspect structural pressure and split candidates.
- `doc_health`: inspect overall documentation health.

Documentation supplies focused context, not authority. When it conflicts with
the implementation, report the contradiction and correct the owning document
only when that update is within scope.
