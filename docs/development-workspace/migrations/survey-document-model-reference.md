---
title: Survey document model reference
aliases: ["Survey document model reference"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-11-20
tags: [backend, frontend]
related_code: []
related_docs: ["FlowForm V2 survey document definition", "FlowForm V2 answer data definition", "Survey document visual guide", "Survey document data structure comparison"]
---

# Survey document model reference

## Current definitions

The current V2 data shapes are defined in:

- [Survey document definition](flowform-v2-survey-document-definition.md)
- [Answer data definition](flowform-v2-answer-data-definition.md)

Those documents take precedence over earlier prototype examples. This page is a
short reading aid, not another contract or a definition of implementation.

## Survey shape

```text
SurveyContent: title, description?
├── sections[]
│   └── section: id, title, description?, blocks[]
│       ├── content block: id, type, content
│       └── input block: id, type, field
│           └── field: id, uuid, prompt, description?,
│                      interaction, answerSpec, behaviour?
└── workflow?.rules[]: id, enabled, when, outcome
```

| Concept | Representation |
| --- | --- |
| Readable identity | `id`; sections, blocks and workflow rules need no UUID. |
| Answerable identity | Fields and selectable items have both `id` and `uuid`. |
| Input presentation | `interaction`; independent of accepted value type. |
| Accepted value | `answerSpec.type`, `required`, optional `constraints`. |
| Local condition | `fieldUuid`, `operator`, applicable comparison `value`. Choice values are option UUIDs. |

Array positions express section/block order. `field.key`, `option.key`, typed
ULIDs and the old field-level `response` property are not the new data shape.

## Individual answer shape

```json
{
  "field_uuid": "10000000-0000-4000-8000-000000000001",
  "client_mutation_id": "60000000-0000-4000-8000-000000000001",
  "state": "answered",
  "answer_spec": {
    "type": "integer",
    "required": true,
    "constraints": { "min": 0, "max": 120 }
  },
  "answer_value": 24
}
```

An answered submission includes both `answer_spec` and `answer_value`. A cleared
submission omits `answer_value` and may omit `answer_spec`. No saved answer means
unanswered. Completion is a separate `{ "action": "complete" }` object; it does
not resubmit a collection of answers.

`answer_spec` mirrors the field's `answerSpec`. It describes the submitted value
without repeating the question text or visual interaction. It permits value
interpretation without loading the whole document; a client-supplied description
is not independent proof of the published field's constraints.

Basic types are string, integer, number, boolean, date, choice and choice_set.
Choice values are option UUIDs; choice sets are arrays of option UUIDs. Structured
values require a corresponding specification: matching uses `pairs`, ranking is
an ordered UUID array, and a single-choice matrix maps row UUIDs to column UUIDs.

The new envelope does not require `answers[]`, `committedAt`, per-answer revision
counters, or a whole-response document. Storage and internal result projections
are separate concerns.

## Examples and companions

- [Survey JSON](assets/survey-document-example.json)
- [Numeric answer JSON](assets/survey-document-feedback-response.json)
- [Choice answer JSON](assets/survey-document-response-example.json)
- [Completion JSON](assets/survey-completion-example.json)
- [Visual guide](survey-document-visual-guide.md)
- [Data comparison](survey-document-data-structure.md)
