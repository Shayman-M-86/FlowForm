---
title: FlowForm V2 survey document definition
aliases: ["FlowForm V2 survey document definition"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-11-18
tags: [backend, frontend]
related_code: []
related_docs: []
---

# FlowForm V2 — Survey Document Definition

## 1. Overview

FlowForm V2 represents surveys as structured documents containing sections, content blocks, questions, and conditional logic.

The structure separates three concepts:

- **Document:** Organises sections and content.
- **Fields:** Define questions, input interactions, and accepted values.
- **Workflow:** Defines survey-level conditions and outcomes.

### Document hierarchy

```text
Survey
├── Metadata
├── Document
│   └── Sections[]
│       └── Blocks[]
│           ├── Content
│           └── Field
│               ├── Interaction
│               ├── AnswerSpec
│               └── Behaviour
└── Workflow
    └── Rules[]
```

Repeatable groups and respondent response structures are outside the scope of this definition.

## 2. Identifiers

FlowForm uses two types of identifiers.

| Identifier | Purpose |
|---|---|
| `id` | Human-readable identifier for structural elements and data fields |
| `uuid` | Stable machine identifier for answerable fields and selectable components |

Sections, blocks, and workflow rules require only an `id`.

Fields and selectable options require both `id` and `uuid`.

Field UUIDs uniquely identify questions regardless of their position in the document. Conditions reference fields and selectable options by UUID.

## 3. Survey structure

### Survey

The root object contains metadata and the document itself.

| Property | Type | Description |
|---|---|---|
| `id` | string | Survey identifier |
| `versionId` | string | Survey version |
| `revision` | integer | Document revision |
| `title` | string | Survey title |
| `description` | string? | Optional description |
| `projectName` | string | Associated project |
| `status` | enum | `draft`, `published`, `archived` |
| `document` | object | Survey content |
| `workflow` | object? | Survey-level rules |

### Document and sections

A document contains an ordered array of sections.

Each section contains:

| Property | Type | Description |
|---|---|---|
| `id` | string | Section identifier |
| `title` | string | Section title |
| `description` | string? | Optional description |
| `blocks` | array | Ordered content blocks |

Section and block order is determined by their position in their respective arrays.

## 4. Blocks

Each block has an `id` and `type`. The type determines its content.

| Type | Purpose | Main properties |
|---|---|---|
| `heading` | Heading text | `content.text`, `content.level` |
| `paragraph` | Descriptive text | `content.text` |
| `notice` | Information or warning | `content.tone`, `content.title`, `content.text` |
| `divider` | Visual separator | No additional properties |
| `input` | Answerable question | `field` |

Additional content types, such as images and videos, may be defined separately.

An `input` block contains a `field` object. Other block types contain a `content` object where applicable.

## 5. Fields

A field represents an answerable question.

| Property | Type | Description |
|---|---|---|
| `id` | string | Human-readable field identifier |
| `uuid` | UUID | Stable question identity |
| `prompt` | string | Question text |
| `description` | string? | Supporting information |
| `interaction` | object | Input type and presentation |
| `answerSpec` | object | Accepted value and constraints |
| `behaviour` | object? | Conditional visibility |

### Interaction

The `interaction` object defines how a participant provides an answer.

| Kind | Presentation examples |
|---|---|
| `short_text` | Text input |
| `long_text` | Textarea |
| `number` | Numeric input, stepper |
| `single_choice` | Radio, dropdown, buttons, cards |
| `multiple_choice` | Checkboxes, buttons, cards |
| `rating` | Slider, stars, scale |
| `boolean` | Yes/no, toggle |
| `date` | Calendar, date input |

Additional interaction types, including ranking, matching, and matrices, can extend this model.

Choice-based interactions contain an `options` array. Each option has a human-readable `id`, a `uuid`, and a display `label`.

### Answer specification

`answerSpec` defines the type of value a field accepts, independently of its visual presentation.

| Property | Type | Description |
|---|---|---|
| `type` | enum | Expected value type |
| `required` | boolean | Whether an applicable field requires an answer |
| `constraints` | object? | Type-specific restrictions |

Supported basic types:

| Type | Accepted value |
|---|---|
| `string` | Text |
| `integer` | Whole number |
| `number` | Numeric value, including decimals |
| `boolean` | True or false |
| `date` | Calendar date |
| `choice` | Single option UUID |
| `choice_set` | Array of option UUIDs |

Constraints vary by type. Examples include numeric minimums and maximums, string lengths, and minimum or maximum selections.

Structured answer types for matrices and ranking require their own definitions.

## 6. Behaviour and conditions

The optional `behaviour` object describes field-level behaviour.

Currently, visibility is the primary supported behaviour.

| Mode | Meaning |
|---|---|
| `always` | Field is always visible |
| `conditional` | Visibility depends on a condition |

A condition references another field using `fieldUuid`.

### Condition structure

| Property | Description |
|---|---|
| `fieldUuid` | UUID of the referenced field |
| `operator` | Comparison operation |
| `value` | Comparison value, when applicable |

Basic operators include:

- `equals`, `not_equals`
- `greater_than`, `less_than`
- `contains`
- `is_answered`

Choice comparisons use option UUIDs rather than labels or readable IDs.

More complex expressions may use `all`, `any`, and `not` to combine conditions.

## 7. Workflow

Workflow contains survey-level rules, separate from individual field behaviour.

Each rule contains:

| Property | Description |
|---|---|
| `id` | Human-readable rule identifier |
| `enabled` | Whether the rule is active |
| `when` | Condition that activates the rule |
| `outcome` | Survey-level result identifier |

Workflow conditions use the same condition structure as field visibility.

Examples of outcomes include eligibility classifications and screening results.

The detailed execution semantics of workflow outcomes are defined separately.

## 8. Example survey

```json
{
  "id": "health_screening",
  "versionId": "version_001",
  "revision": 1,
  "title": "Health Screening",
  "projectName": "Health Research",
  "status": "draft",
  "document": {
    "sections": [
      {
        "id": "eligibility",
        "title": "Eligibility",
        "blocks": [
          {
            "id": "age_input",
            "type": "input",
            "field": {
              "id": "age",
              "uuid": "10000000-0000-4000-8000-000000000001",
              "prompt": "How old are you?",
              "interaction": {
                "kind": "number",
                "suffix": "years"
              },
              "answerSpec": {
                "type": "integer",
                "required": true,
                "constraints": {
                  "min": 0,
                  "max": 120
                }
              }
            }
          },
          {
            "id": "smoking_input",
            "type": "input",
            "field": {
              "id": "smoking_status",
              "uuid": "10000000-0000-4000-8000-000000000002",
              "prompt": "Do you smoke?",
              "interaction": {
                "kind": "single_choice",
                "presentation": "radio",
                "options": [
                  {
                    "id": "yes",
                    "uuid": "20000000-0000-4000-8000-000000000001",
                    "label": "Yes"
                  },
                  {
                    "id": "no",
                    "uuid": "20000000-0000-4000-8000-000000000002",
                    "label": "No"
                  }
                ]
              },
              "answerSpec": {
                "type": "choice",
                "required": true
              }
            }
          }
        ]
      }
    ]
  },
  "workflow": {
    "rules": [
      {
        "id": "underage",
        "enabled": true,
        "when": {
          "fieldUuid": "10000000-0000-4000-8000-000000000001",
          "operator": "less_than",
          "value": 18
        },
        "outcome": "ineligible_underage"
      }
    ]
  }
}
```

## 9. Core principles

1. The document maintains a section-and-block hierarchy suited to visual survey building.
2. Structural elements use human-readable identifiers; answerable fields and options additionally use UUIDs.
3. Input presentation and accepted answer types remain separate.
4. Conditional logic uses stable field references.
5. Workflow rules are separate from the document's content.
6. Survey definitions are versioned, with their content and ordering preserved within each version.

This definition establishes the structure of a FlowForm V2 survey without specifying API endpoints, database storage, compilation processes, or respondent response formats.