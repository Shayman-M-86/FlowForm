---
title: Builder and rules
aliases:
  - "Builder and rules"
document_type: domain
status: draft
authority: canonical
verified_against_commit: ad26b87e9820
tags: [frontend]
related_code:
  - "../../frontend/packages/builder/src/"
  - "../../frontend/packages/schema/src/generated/"
  - "../../frontend/apps/studio-app/src/pages/SurveyWorkspaceTabPages/useSurveyBuilderController.ts"
  - "../../frontend/apps/studio-app/src/pages/RespondPage.tsx"
  - "../../backend/app/services/content.py"
  - "../../backend/app/schema/api/requests/content/"
related_docs:
  - "Surveys and versioning"
  - "Frontend implementation"
---

# Builder and rules

Defines the editable survey-node model, authoring behavior, and client-side rule
runtime shared by the Studio builder and form filler. The durable lifecycle of
the version containing those nodes belongs to
[[surveys-and-versioning|Surveys and versioning]].

## Purpose

This domain turns a survey version into an ordered graph of questions and rules
that an author can edit and a respondent can traverse. It keeps frontend editing
types aligned with backend request schemas while separating unsaved browser
state from persisted draft content.

## Responsibilities

- Edit ordered question and rule nodes with stable UUIDs, human-readable node
  keys, sort keys, and validated content.
- Support choice, field, matching, and rating question families.
- Express rule predicates with `ALL`, `ANY`, or `NONE`, change question
  visibility/required state, jump to a target, or end by submitting/discarding.
- Persist draft nodes and scoring rules through version-scoped backend APIs.
- Recover unsaved Studio draft state from version-scoped browser storage.
- Execute the published node graph in the shared form filler, validate the
  current answer, and report answer commits and completion to its consumer.
- Carry scoring-rule definitions for choice mapping, matching keys, direct
  ratings, and numeric ranges in backend content and compiled publication data.

## Non-responsibilities

- The builder does not publish or archive versions by itself; the Studio
  controller invokes the survey-version APIs.
- It does not authorize edits or submission access.
- It does not encrypt or persist respondent answers directly. `RespondPage`
  translates committed filler answers into respondent API commands.
- The browser recovery copy is not authoritative; persisted draft rows in core
  data remain the server-side source of truth.

## Main entities and invariants

| Entity | Shape | Important invariant |
| --- | --- | --- |
| Survey node | Question or rule with UUID, `node_key`, `sort_key`, and content | Node key and sort key are unique within one version; sort keys are positive. |
| Question node | `choice`, `field`, `matching`, or `rating` content | Request schemas reject unknown fields and family-incompatible definitions. |
| Rule node | Predicate plus `then` and optional `else` branches | Conditions and branch actions are shape-validated; targets use editable node keys. |
| Scoring rule | Unique scoring key plus typed strategy document | Scoped to one survey version and included in the compiled publication snapshot. |
| Browser draft | Version-scoped serialized node array | Best-effort local recovery only; invalid or inaccessible storage is ignored. |
| Filler progress | Answers, committed node keys, and derived presentation state | Nodes are evaluated in sort order with a loop counter and explicit invalid-flow result. |

The backend permits content mutation only while the containing version is
`draft`; PostgreSQL triggers independently reject changes to published content.
Generated `@flowform/schema` types derive from the backend contract and are
consumed by the builder package.

## Important workflows

1. Studio loads versions and nodes, chooses a draft when available, and recovers
   a different unsaved browser copy when one exists.
2. `NodePage` adds, edits, removes, and reorders local nodes and derives valid
   sibling targets for rule editing.
3. Save validates required authoring fields, diffs local and server nodes, then
   issues version-scoped deletes, creates, and updates before replacing the
   query cache with returned server state.
4. Publishing first saves dirty draft state, then invokes the version publication
   flow that snapshots nodes and scoring rules.
5. Respondent rendering normalizes published nodes, executes rule branches in
   `FormFiller`, sends each committed question answer to the backend, waits for
   in-flight saves, and finally completes the submission session.

## Implementation map

- `frontend/packages/builder/src/pages/builder/` owns node creation, ordering,
  rule relationships, and the full-page editor.
- `frontend/packages/builder/src/components/form_filler/` owns rule evaluation,
  per-family answer validation, progress, and completion results.
- `frontend/apps/studio-app/src/pages/SurveyWorkspaceTabPages/useSurveyBuilderController.ts`
  integrates browser recovery, permissions, API mutations, and version actions.
- `frontend/apps/studio-app/src/pages/RespondPage.tsx` adapts compiled nodes and
  filler callbacks to respondent answer/session APIs.
- `backend/app/schema/api/requests/content/`, `services/content.py`, and
  `repositories/content_repo.py` validate and persist version-scoped content.
- Backend integration tests cover node/scoring persistence and version cloning;
  Studio tests cover browser draft storage.

## Verified gaps and open questions

- The publication compiler writes `node_id`, `type`, `sort_key`, and `content`
  but omits the authored `node_key`. `RespondPage` currently substitutes
  `node_id` as the runtime key, while rule conditions and jump targets still
  contain authored node keys; published rule references therefore need an
  explicit, tested normalization contract.
- Rule traversal, visibility, and required-question enforcement occur in the
  frontend filler. The backend validates individual answer shapes but does not
  re-evaluate the compiled rule graph or requiredness before completion.
- Saving a draft is a sequence of independent node API mutations, not one
  aggregate transaction. A mid-save failure can leave a partially applied
  server draft for the next reload/retry to reconcile.
- Whole-graph validation does not reject missing targets or loops at authoring or
  publication time; the filler detects those conditions only while executing.
- No focused automated tests for the shared builder rule runtime were found.
- Backend scoring-rule APIs and publication exist, but the inspected Studio
  builder has no scoring-rule authoring surface or result-scoring execution path.

## Related documents

- [[surveys-and-versioning|Surveys and versioning]]
- [[frontend|Frontend implementation]]
