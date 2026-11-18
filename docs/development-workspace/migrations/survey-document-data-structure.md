---
title: Survey document data structure comparison
aliases: ["Survey document data structure comparison"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-11-18
tags: [backend, frontend]
related_code:
  - "../../../backend/app/schema/models/survey/document.py"
  - "../../../backend/app/services/surveys.py"
  - "../../../backend/app/schema/models/survey/fields.py"
  - "../../../backend/app/schema/api/requests/submission_sessions.py"
  - "../../../backend/app/schema/orm/core/submission_answer_slot.py"
  - "../../../backend/app/crypto/_internal/models.py"
related_docs: ["FlowForm V2 survey document definition", "FlowForm V2 answer data definition", "Survey document reconciliation plan"]
---

# Survey document data structure comparison

[Open the simplified HTML presentation](assets/flowform-data-structure.html).
Use Arrow keys or Space to navigate, F for fullscreen, and E to edit. Ctrl+S/Cmd+S
downloads an edited copy. The file includes its fonts and needs no build step.

The current V2 [survey](flowform-v2-survey-document-definition.md) and
[answer](flowform-v2-answer-data-definition.md) definitions are the data sources.
This comparison does not add implementation requirements to them.

## Current and suggested representations

| Area | Pre-migration reconsolidation | V2 data shape |
| --- | --- | --- |
| Content | Ordered question/rule rows; separate scoring; compiled snapshot. | Survey metadata, ordered sections and blocks, fields and workflow. |
| Identity | Node UUID, readable node key, numeric sort key. | Readable id; field/option uuid; array order. |
| Question | Family-specific content/definition. | interaction + answerSpec + optional behaviour. |
| Condition reference | Earlier node/key model. | fieldUuid and option UUID values. |
| Answer | Question-node identity and family-shaped request. | field_uuid + mutation ID + state + answer_spec + answer_value. |
| Completion | Separate session completion. | Separate action complete; no answer collection. |

The pre-migration implementation already had JSONB, UUID identity, per-answer saving and a published
snapshot. V2 reorganizes these concepts. Shared schemas are being migrated ahead of runtime callers.

## Naming at the boundary

| Survey definition | Answer submission |
| --- | --- |
| field.uuid | field_uuid |
| field.answerSpec | answer_spec |
| answerSpec.type | Determines the type of answer_value. |
| interaction.options[].uuid | Stored choice values and choice-set entries. |
| behaviour condition.fieldUuid | References another field UUID within the survey. |

An answered submission includes its expected specification as data. Its presence
allows interpretation without retrieving the complete survey, but does not prove
that the client's constraints match the published field.

## What the updated presentation omits

The earlier typed-ULID model, field/option keys, per-answer revision counters,
whole-response arrays and assumed automatic workflow termination are no longer
shown as the target. Root survey revision remains part of the document data.

Matching uses a pairs object, choice sets use arrays of option UUIDs, ranking
uses an ordered option-UUID array, and a single-choice matrix maps row UUIDs to
column UUIDs. Structured contents still need a corresponding answer_spec; a
bare object/array type does not define them completely.

## Scope and sources

The comparison describes the pre-migration node model. Its node request and
question-content schema files have been removed during consolidation. Current
schema definitions and the publication implementation are available here:

- [Document schema](../../../backend/app/schema/models/survey/document.py)
- [Field schema](../../../backend/app/schema/models/survey/fields.py)
- [Publication implementation](../../../backend/app/services/surveys.py)
- [Answer request](../../../backend/app/schema/api/requests/submission_sessions.py)

The guide does not define HTTP routes, database columns or an execution engine.
Feature implementation remains excluded from the migration. See the
[reconciliation plan](survey-document-reconciliation-plan.md) for the separate
implementation work.
