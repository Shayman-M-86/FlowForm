---
title: Survey document reconciliation plan
aliases: ["Survey document reconciliation plan"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-11-18
tags: [backend, frontend]
related_code:
  - "../../../backend/app/services/surveys.py"
  - "../../../backend/app/services/public_submissions/api/session_management.py"
  - "../../../frontend/scripts/generate-types.mjs"
  - "../../../frontend/apps/studio-app/src/pages/SurveyWorkspaceTabPages/useSurveyBuilderController.ts"
  - "../../../frontend/apps/studio-app/src/pages/RespondPage.tsx"
related_docs: ["FlowForm V2 survey document definition", "FlowForm V2 answer data definition", "Survey document model reference", "Survey document visual guide", "Survey document data structure comparison"]
---

# Survey document reconciliation plan

## Direction

Implement the document model afresh on reconsolidation. Use the current V2
[survey definition](flowform-v2-survey-document-definition.md) and
[answer definition](flowform-v2-answer-data-definition.md) as the data references.
Feature and Test-suite are background material, not contracts to copy.

Do not migrate feature's frontend or backend implementation. Preserve the
working reconsolidation behavior and adapt it to the new data shapes. Prototype
component reuse remains a separate decision.

## What changes in the data

| Current representation | V2 representation |
| --- | --- |
| Question/rule rows and a compiled node snapshot | Survey metadata plus ordered sections and blocks, fields and workflow. |
| Node UUID, node key and sort key | Readable structural IDs; fields/options also have UUIDs; arrays express order. |
| Question family and definition | Separate `interaction`, `answerSpec` and optional `behaviour`. |
| Conditions tied to the earlier model | Field references use `fieldUuid`; choice comparisons use option UUIDs. |
| Question-node answer identity and family envelope | `field_uuid`, `client_mutation_id`, `state`, `answer_spec`, `answer_value`. |

Root `revision` describes the survey document. Per-answer revisions and a flat
whole-response `answers[]` object from earlier examples are not required by the
new answer definition. Each answered submission carries its specification;
clearing and completion have distinct shapes.

## Areas to adapt

| Area | Change to assess | Current behavior to preserve |
| --- | --- | --- |
| Studio | Document editing and saving; UUID identity; new field shape. | Permissions, draft recovery, dirty state, version switching and read-only published views. |
| AI import | Generate definitions using the new field/answerSpec structure. | Server-side calls, limits, permissions and preview experience. |
| Respondent | Render the document; submit individual self-describing answers. | Entry-scoped resume, pinned versions, acknowledged saves, clearing and completion. |
| Results | Resolve UUIDs to readable question/option metadata. | Authorized access, readable wording, ordering and exports. |
| Contracts and storage | Represent the new data without assuming it dictates database/API design. | Generated-contract consistency, core/response separation and encryption safeguards. |

Submitted `answer_spec` describes the expected value but is not proof of the
published field's constraints. The verification mechanism is implementation work;
the data definition does not prescribe loading the entire survey for each save.

## Remaining implementation work

1. Capture the working reconsolidation baseline and regression coverage.
2. Map the V2 definitions to current services and contracts without importing
   feature code or silently changing the data definitions.
3. Adapt authoring, AI import, respondent flow and results in an isolated candidate.
4. Verify the complete create/publish/answer/resume/complete/results/export journey.
5. Agree data transition and deployment details before activation.

Advanced interactions, compound-condition details and workflow execution should
be specified separately where the V2 definitions leave them open. An outcome
identifier alone does not define automatic termination or rule precedence.

## Context and evidence

The initial comparison used reconsolidation `d7c4dc07`, feature `e088fbb9` and
common ancestor `02134e66`. It found 62 reconsolidation-only commits, 16
feature-only commits and 42 conflicted paths in a merge rehearsal. These are
historical assessment results, not fresh checks or a reason to merge feature.

The fresh implementation has not started. No database reset or deployment is
part of this documentation update.

## Reading aids

[Model summary](survey-document-model-reference.md) ·
[Visual guide](survey-document-visual-guide.md) ·
[Data comparison](survey-document-data-structure.md)
