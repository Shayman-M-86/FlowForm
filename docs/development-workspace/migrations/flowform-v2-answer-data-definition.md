---
title: FlowForm V2 answer data definition
aliases: ["FlowForm V2 answer data definition"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-11-18
tags: [backend, frontend]
related_code: []
related_docs: []
---

# FlowForm V2 — Answer Data Definition

## 1. Overview

FlowForm V2 submits answers individually as respondents complete a survey.

Each answer identifies a field in the published survey definition and includes its expected answer specification alongside the submitted value.

The structure consists of four concepts:

- **Answer envelope:** Identifies the field and submission operation.
- **Answer specification:** Declares the expected value type and its constraints.
- **Answer value:** Contains the respondent's actual answer.
- **Answer state:** Indicates whether the answer is being saved or cleared.

Each submission is self-describing. The backend can interpret and validate the submitted value using the included `answer_spec`, without retrieving the complete survey definition.

A complete collection of answers is not submitted. Survey completion is a separate operation.

## 2. Answer structure

| Property | Type | Description |
|---|---|---|
| `field_uuid` | UUID | Identifies the answerable field in the survey definition |
| `client_mutation_id` | UUID | Identifies this submission operation |
| `state` | enum | `answered` or `cleared` |
| `answer_spec` | object | Declares the expected answer type and constraints |
| `answer_value` | variable | Submitted value, present when answered |

The `field_uuid` is the canonical identifier, rather than the field's human-readable `id`.

### Answer states

| State | Meaning |
|---|---|
| `answered` | The submission contains an answer value |
| `cleared` | An existing answer is explicitly cleared |

When `state` is `answered`, both `answer_spec` and `answer_value` are required.

When `state` is `cleared`, `answer_value` is omitted. The `answer_spec` may also be omitted because no value requires validation.

A field with no saved answer is considered unanswered.

## 3. Answer specification

The `answer_spec` accompanies each submitted answer and describes the expected structure of its value.

It follows the same definition used by the corresponding field's `answerSpec` in the survey document.

| Property | Type | Description |
|---|---|---|
| `type` | enum | Expected answer value type |
| `required` | boolean | Whether the field requires an answer when applicable |
| `constraints` | object? | Type-specific value restrictions |
| `items` | object? | Definition of elements within an array |
| `valueType` | enum? | Value type within certain structured objects |

The specification describes the value independently of the question's visual interaction.

For example, a slider and a numeric text input may both submit an integer value using the same answer specification.

### Supported answer types

| Type | Expected value | Possible constraints |
|---|---|---|
| `string` | Text | `minLength`, `maxLength` |
| `integer` | Whole number | `min`, `max` |
| `number` | Numeric value | `min`, `max` |
| `boolean` | True or false | — |
| `date` | Date string | Date bounds |
| `choice` | Single option UUID | — |
| `choice_set` | Collection of option UUIDs | `minSelections`, `maxSelections` |
| `object` | Structured object | Structure-specific constraints |
| `array` | Structured array | `minItems`, `maxItems`, `uniqueItems` |

For `choice` and `choice_set`, the specification defines the expected value type and cardinality. It does not necessarily carry the complete list of selectable options.

For structured values, additional properties describe the required shape.

### Example — Numeric specification

```json
{
  "type": "integer",
  "required": true,
  "constraints": {
    "min": 0,
    "max": 120
  }
}
```

### Example — Multiple-choice specification

```json
{
  "type": "choice_set",
  "required": true,
  "constraints": {
    "minSelections": 1,
    "maxSelections": 3
  }
}
```

## 4. Answer value types

The `answer_value` contains the respondent's answer. Its structure is determined by `answer_spec.type`, not by the question's interaction or presentation.

### Basic values

| Type | JSON value | Example |
|---|---|---|
| `string` | String | `"Hello"` |
| `integer` | Integer | `24` |
| `number` | Number | `7.5` |
| `boolean` | Boolean | `true` |
| `date` | Date string | `"2026-11-18"` |
| `choice` | Option UUID | `"20000000-0000-4000-8000-000000000001"` |
| `choice_set` | Array of option UUIDs | `["option-uuid-1", "option-uuid-2"]` |

### Structured values

Some question types require structured values.

**Matching**

An array of prompt-to-match associations, preserving the existing answer model's `pairs` structure.

```json
{
  "pairs": [
    {
      "prompt_uuid": "30000000-0000-4000-8000-000000000001",
      "match_uuid": "40000000-0000-4000-8000-000000000002"
    }
  ]
}
```

**Ranking**

An ordered array of option UUIDs, where array position represents rank.

```json
[
  "option-uuid-3",
  "option-uuid-1",
  "option-uuid-2"
]
```

**Matrix**

An object mapping row UUIDs to selected column UUIDs for a single-choice matrix.

```json
{
  "row-uuid-1": "column-uuid-2",
  "row-uuid-2": "column-uuid-3"
}
```

These structures must be described by their corresponding `answer_spec`. An `object` or `array` type alone does not specify the permitted contents.

## 5. Answer examples

### Numeric answer

```json
{
  "field_uuid": "10000000-0000-4000-8000-000000000001",
  "client_mutation_id": "60000000-0000-4000-8000-000000000001",
  "state": "answered",
  "answer_spec": {
    "type": "integer",
    "required": true,
    "constraints": {
      "min": 0,
      "max": 120
    }
  },
  "answer_value": 24
}
```

### Single-choice answer

```json
{
  "field_uuid": "10000000-0000-4000-8000-000000000002",
  "client_mutation_id": "60000000-0000-4000-8000-000000000002",
  "state": "answered",
  "answer_spec": {
    "type": "choice",
    "required": true
  },
  "answer_value": "20000000-0000-4000-8000-000000000001"
}
```

### Multiple-choice answer

```json
{
  "field_uuid": "10000000-0000-4000-8000-000000000003",
  "client_mutation_id": "60000000-0000-4000-8000-000000000003",
  "state": "answered",
  "answer_spec": {
    "type": "choice_set",
    "required": false,
    "constraints": {
      "minSelections": 0,
      "maxSelections": 3
    }
  },
  "answer_value": [
    "20000000-0000-4000-8000-000000000004",
    "20000000-0000-4000-8000-000000000005"
  ]
}
```

### Matching answer

```json
{
  "field_uuid": "10000000-0000-4000-8000-000000000004",
  "client_mutation_id": "60000000-0000-4000-8000-000000000004",
  "state": "answered",
  "answer_spec": {
    "type": "object",
    "required": true,
    "valueType": "matching"
  },
  "answer_value": {
    "pairs": [
      {
        "prompt_uuid": "30000000-0000-4000-8000-000000000001",
        "match_uuid": "40000000-0000-4000-8000-000000000002"
      }
    ]
  }
}
```

### Rating answer

```json
{
  "field_uuid": "10000000-0000-4000-8000-000000000005",
  "client_mutation_id": "60000000-0000-4000-8000-000000000005",
  "state": "answered",
  "answer_spec": {
    "type": "integer",
    "required": true,
    "constraints": {
      "min": 0,
      "max": 10
    }
  },
  "answer_value": 8
}
```

### Cleared answer

```json
{
  "field_uuid": "10000000-0000-4000-8000-000000000001",
  "client_mutation_id": "60000000-0000-4000-8000-000000000006",
  "state": "cleared"
}
```

## 6. Survey completion

Survey completion is independent of individual answer submissions.

A completion request signals that the respondent has finished the survey without resubmitting previously saved answers.

```json
{
  "action": "complete"
}
```

The submission session and published survey version are identified by the surrounding request context.

## 7. Core principles

1. Each answer is submitted independently as it is entered, changed, or cleared.
2. Fields and selectable options are identified using UUIDs.
3. Every answered submission includes an `answer_spec` describing its expected value type and constraints.
4. The backend can interpret and validate an answer using its submitted specification without loading the complete survey definition.
5. The submitted specification is a client-provided description of the expected value, not independent proof of the published field's constraints.
6. Answer state and answer value are separate concepts.
7. Answer values do not duplicate question text, labels, or presentation settings.
8. Survey completion is independent of answer submissions and does not contain previously submitted answers.
9. The response format is independent of database storage, encryption, and API routing.