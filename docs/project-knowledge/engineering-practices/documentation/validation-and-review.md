---
title: Documentation validation and review
aliases: ["Documentation validation and review"]
document_type: overview
status: verified
authority: canonical
verified_evidence_digest: sha256:f1112810cb34d3368a61d725b9d5aae5a3aa01ee176c60e05d2680e7ab930840
last_edited: 2026-07-27
tags: [meta]
related_code:
  - "../../../../tools/docs/docsys/"
  - "../../../../tools/docs/hooks/"
  - "../../../../tools/docs/validate-agent-setup.py"
  - "../../../../.codex/hooks.json"
  - "../../../../.claude/settings.json"
  - "../../../../.agents/skills/flowform-doc-context/"
  - "../../../../.agents/skills/flowform-doc-verification/"
  - "../../../../.claude/agents/docs-maintainer.md"
  - "../../../../.claude/skills/flowform-doc-context/"
  - "../../../../.claude/skills/flowform-doc-verification/"
  - "../../../../.codex/agents/docs-maintainer.toml"
related_docs:
  - "Documentation practice"
  - "Documentation model"
  - "Documentation authoring guide"
---

# Documentation validation and review

Describes how FlowForm documentation is validated and reviewed: the `docsys`
profiles that gate structure, the review checklist authors apply per group, and
why maintainability debt stays advisory.

## Validation profiles

`docsys validate` applies shared rules through collection-aware profiles. The
same objective defect maps to a different severity depending on the profile and
the document's collection:

| Profile             | Purpose                                                                              |
| ------------------- | ------------------------------------------------------------------------------------ |
| `editing`           | Advisory; everything is a warning while a document is being written.                 |
| `project-knowledge` | Errors for Project Knowledge; other collections stay advisory.                       |
| `workspace`         | Errors for Development workspace, but optional metadata stays advisory there.        |
| `commit`            | Gates objective structural defects in both collections at commit time.               |
| `ci`                | The CI gate; objective structural defects are errors in both collections.            |

Structural defects that gate under `commit`/`ci` include missing folder heads,
documents with no inferable structural parent, duplicate titles, unresolved
`related_docs`, unresolved wiki links, broken Markdown links, workspace documents
claiming canonical authority, and documents placed outside the two collections.

Optional workspace metadata — `aliases`, `authority`, `related_code`,
`related_docs`, `verified_evidence_digest`, `last_edited` — stays advisory for
Development workspace documents, so honest incompleteness there does not fail
CI.

Evidence verification is not a Development Workspace gate. Workspace pages
remain working material rather than being promoted to `verified`.

```text
authored documentation
          |
          +--> metadata and parent checks
          +--> title and link resolution
          +--> collection/authority rules
          +--> generated-file policy
          |
          v
 editing --> project/workspace --> commit --> CI
 warnings       scoped gates       gate     gate
          |
          +--> advisory debt and human content review
```

## Running validation

Validate the collection tree and review advisory debt from the repository root:

```sh
PYTHONPATH=tools/docs python3 -m docsys validate \
  --docs-root docs --profile ci
PYTHONPATH=tools/docs python3 -m docsys debt \
  --docs-root docs --changed --suggest-splits
```

Run the documentation tooling's own tests when changing `docsys`:

```sh
PYTHONPATH=tools/docs python3 -m unittest discover -s tools/docs/tests -v
```

When changing agent skills, documentation-maintainer definitions, or MCP registration,
run the dependency-free shared validator:

```sh
python3 tools/docs/validate-agent-setup.py
```

It verifies that Codex and Claude carry the same documentation-context skill,
the same user-approval verification skill, a `docs-maintainer`, and the same
`flowform-docs` MCP server. It does not depend on PyYAML or a preconfigured
Python environment.

Codex and Claude also use the same three hook events and the same implementations
under `tools/docs/hooks/`: session baseline capture, lightweight Python
post-edit quality checks, and non-blocking documentation-impact review at task
completion. Agent configuration contains only pointers to those shared scripts.

These checks validate structure and resolution, not factual correctness. Review
against implementation evidence remains required.

## Reliability disclosure during retrieval

`get_task_context` returns a `documentation_reliability` assessment for its
primary documents. It combines status, `verified_evidence_digest`, freshness,
and working-tree state so an agent does not silently present unfinished or
changing documentation as confirmed behaviour.

An agent must surface the returned message when `requires_disclosure` is true.
A clean draft with no verification baseline is **provisional**: its explanation
may be useful, but it is not verified. A scaffold, a materially stale page, an
unknown verification baseline on a page marked verified, or a primary document
with uncommitted edits is **unreliable for the current question**. The signal is
an exploration and disclosure guard; it does not prove that a particular claim
is false.

For explanation-only requests, agents should synthesize after an initial pass
of 5–10 files and 2–3 focused searches. They ask before widening that work into
a broad audit. Explicit verification, diagnosis, or implementation requests may
continue as far as necessary to produce the requested result.

When repository evidence contradicts a material Project Knowledge claim:

1. report the document claim and conflicting evidence;
2. correct the page when documentation editing is in scope;
3. set `status: draft` and clear `verified_evidence_digest`;
4. stage the implementation and documentation changes;
5. after semantic review, run `docsys evidence promote --staged` for the revised
   page before committing it as `verified`.

Read-only investigations report the required metadata change without modifying
the repository. Draft status alone is not a contradiction, and an agent must
not claim one without implementation evidence.

## Staged verification gate

The Git pre-commit hook uses Docsys impact confidence before comparing affected
verified Project Knowledge documents with the exact implementation blobs in the
staged index. An exact file named in `related_code` is high confidence: when
that change invalidates a digest, Docsys changes the document to `draft`, clears
the digest, stages the metadata update, and stops the commit attempt for review.
Broader directory, glob, and `change_triggers` matches keep their verified
status; the hook refreshes their evidence digest and allows the commit to
continue. A document edited in the same commit is always checked regardless of
impact confidence.

The hook never promotes an invalidated document: an agent or author must first
perform the semantic evidence review and run `docsys evidence promote --staged`.

This keeps the workflow to one final commit. The digest is stable because it
excludes documentation content, avoiding a self-reference to the commit being
created. The gate is local pre-commit automation and is not repeated in CI.
Development Workspace documents bypass it entirely.

Before that check, the hook sets `last_edited` to the current `YYYY-MM-DD` date
for every staged Markdown document under `docs/` and re-stages the metadata.
Partially staged documents are rejected so the date cannot accidentally pull
unstaged prose into the commit.

## Review checklist

For each completed group, check:

- every current-state claim has an implementation evidence path;
- every folder head stands alone as a high-level explanation, with navigation
  subordinate to its model, boundaries, and synthesis;
- no directory exists only to reserve a future category;
- metadata matches the document's actual maturity and scope;
- wiki links resolve to note targets, while `related_docs` and `aliases` use the
  exact document title;
- controlled tags add cross-cutting value and do not repeat the branch;
- explanations are not duplicated across documents or abstraction levels;
- uncertainties and contradictions remain visible;
- no unrelated scaffold was filled opportunistically.

## Debt is advisory

`docsys debt` separately reports maintainability pressure and split candidates.
A debt finding requires several independent signals before it fires, and it is
downgraded to information for unverified workspace documents. Debt findings
identify where a document may contain several independently maintainable topics;
they do not establish that a document is incorrect and never make an otherwise
valid document fail validation. Split a document only after debt analysis
confirms several independently useful topics are present.

## Related documents

- [[documentation-index|Documentation practice]]
- [[documentation-model|Documentation model]]
- [[authoring-guide|Documentation authoring guide]]
