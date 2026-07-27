---
title: Documentation validation and review
aliases: ["Documentation validation and review"]
document_type: overview
status: draft
authority: canonical
verified_against_commit: null
tags: [meta]
related_code:
  - "../../../../scripts/docs/docsys/"
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
`related_docs`, `verified_against_commit` — stays advisory for
Development workspace documents, so honest incompleteness there does not fail
CI.

## Running validation

Validate the collection tree and review advisory debt from the repository root:

```sh
PYTHONPATH=scripts/docs python3 -m docsys validate \
  --docs-root docs-new --profile ci
PYTHONPATH=scripts/docs python3 -m docsys debt \
  --docs-root docs-new --changed --suggest-splits
```

Run the documentation tooling's own tests when changing `docsys`:

```sh
PYTHONPATH=scripts/docs python3 -m unittest discover -s scripts/docs/tests -v
```

These checks validate structure and resolution, not factual correctness. Review
against implementation evidence remains required.

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
