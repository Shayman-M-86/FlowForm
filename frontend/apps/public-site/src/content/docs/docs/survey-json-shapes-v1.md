---
title: Survey JSON Shapes v1
description: ""
---

# Survey JSON Shapes v1

## Purpose

This document defines the current JSON shapes for:

- questions
- answers / stored response payloads
- rules
- scoring

It also makes the expected **request body shape** explicit for creation endpoints.

Scoring is intentionally left blank for now.

---

## 1. Questions

### Purpose

Questions are stored as JSON in `question_schema`.

Each question follows one shared outer shape:

- `family`
- `label`
- `schema`
- `ui`

`family` determines the inner schema.

### Stored JSON shape (`question_schema`)

```json
{
  "label": "...",
  "family": "...name...",
  "...name...": {
    "schema": {},
    "ui": {}
  }
}
```

### Families

#### Choice

```json
{
  "label": "Select your hobbies",
  "family": "choice",
  "choice": {
    "schema": {
      "options": [
        { "id": "A", "label": "Reading" },
        { "id": "B", "label": "Traveling" },
        { "id": "C", "label": "Cooking" }
      ],
      "min_selected": 1,
      "max_selected": 3
    },
    "ui": {
    }
  }
}
```

#### Field

```json
{
  "label": "What is your email address?",
  "family": "field",
  "field": {
    "schema": {
      "field_type": "email"
    },
    "ui": {
      "placeholder": "name@example.com"
    }
  }
}
```

#### Matching

```json
{
  "label": "Match each country to its capital city",
  "family": "matching",
  "matching": {
    "schema": {
      "prompts": [
        { "id": "p_A", "label": "Australia" },
        { "id": "p_B", "label": "France" }
      ],
      "matches": [
        { "id": "m_A", "label": "Canberra" },
        { "id": "m_B", "label": "Paris" },
        { "id": "m_C", "label": "Madrid" }
      ]
    },
    "ui": {
    }
  }
}
```

#### Rating

```json
{
  "label": "How satisfied are you?",
  "family": "rating",
  "rating": {
    "schema": {
      "range": { 
        "min": -5,
        "max": 5
      },
      "left_label": "Not satisfied",
      "right_label": "Very satisfied"
    },
    "ui": {
      "style": "slider",
      "step": 1
    }
  }
}
```

### Create question request body

```json
{
  "question_key": "q_favourite_colour",
  "question_schema": {
    "family": "choice",
    "label": "What is your favourite colour?",
    "schema": {
      "options": [
        { "id": "a1", "label": "Red" },
        { "id": "a2", "label": "Blue" }
      ],
      "min_selected": 1,
      "max_selected": 1
    },
    "ui": {
      "style": "radio"
    }
  }
}
```

### Constraints

- `question_schema` must be a JSON object.
- `question_schema` must contain the shared top-level shape: `family`, `label`, `schema`, `ui`.
- `family` must be one of: `choice`, `field`, `matching`, `rating`.
- `label` is the human-readable question text.
- `schema` contains family-specific structure and validation rules.
- `ui` contains presentation details only.
- `question_key` must be unique per survey version.
- Backend validation should enforce deeper family-specific rules such as:
  - valid option arrays for choice questions
  - valid `field_type` for field questions
  - valid left/right item arrays for matching questions
  - valid `min` / `max` for rating questions

---

## 2. Answers / Stored response payloads

### Purpose

Each stored answer row keeps `question_key`, `answer_family`, and `answer_value` outside the JSON.

The JSON stored in `answer_value` is only the family-specific payload.

### Base rule

There is no wrapper object inside `answer_value`.

Do not duplicate:

- `question_key`
- `answer_family`
- metadata

inside `answer_value`.

### Stored JSON shapes (`answer_value`)

#### Choice

```json
{
  "selected": ["a2"]
}
```

#### Field

```json
{
  "value": "name@example.com"
}
```

#### Matching

```json
{
  "matches": [
    { "left_id": "c1", "right_id": "r1" }
  ]
}
```

#### Rating

```json
{
  "value": 4
}
```

### Submission request body

This is the request body shape used to create a submission.

```json
{
  "is_anonymous": false,
  "started_at": "2026-04-08T21:00:00Z",
  "submitted_at": "2026-04-08T21:02:00Z",
  "answers": [
    {
      "question_key": "q_favourite_colour",
      "answer_family": "choice",
      "answer_value": {
        "selected": ["a2"]
      }
    },
    {
      "question_key": "q_email",
      "answer_family": "field",
      "answer_value": {
        "value": "name@example.com"
      }
    },
    {
      "question_key": "q_match_capitals",
      "answer_family": "matching",
      "answer_value": {
        "matches": [
          { "left_id": "c1", "right_id": "r1" }
        ]
      }
    },
    {
      "question_key": "q_satisfaction",
      "answer_family": "rating",
      "answer_value": {
        "value": 4
      }
    }
  ],
  "metadata": {}
}
```

### Constraints

- `answer_value` must be a JSON object.
- `answer_family` must determine the allowed JSON shape.
- Formats must not be mixed across families.
- `choice` uses `{ "selected": [...] }`.
- `field` uses `{ "value": ... }`.
- `matching` uses `{ "matches": [...] }`.
- `rating` uses `{ "value": number }`.
- IDs in answers must match IDs defined by the related question schema.
- `choice.selected` is always an array, even for single-select questions.
- `rating.value` must fit within the related question’s `min` / `max`.
- `metadata` is request-level metadata, not answer-level payload.

---

## 3. Rules

### Purpose

Rules define declarative browser-side survey behaviour.

They are not trigger-based.

Each rule describes:

- a `target`
- a `condition`
- one or more `effects`

The browser evaluates rules against current answer state while the user is filling out the survey.

### Stored JSON shape (`rule_schema`)

```json
{
  "target": "q3",
  "condition": {},
  "effects": {}
}
```

### Current project extension

We also allow:

```json
{
  "target": "q3",
  "sort_order": 20,
  "condition": {},
  "effects": {}
}
```

`sort_order` is used for deterministic conflict resolution.

### Create rule request body

```json
{
  "rule_key": "show_q3_when_q1_is_yes",
  "rule_schema": {
    "target": "q3",
    "sort_order": 20,
    "condition": {
      "fact": "answers.q1",
      "operator": "equals",
      "value": "yes"
    },
    "effects": {
      "visible": true
    }
  }
}
```

### Condition shapes

#### Simple

```json
{
  "fact": "answers.q1",
  "operator": "equals",
  "value": "a2"
}
```

#### Grouped AND

```json
{
  "all": [
    {
      "fact": "answers.q1",
      "operator": "equals",
      "value": "a2"
    },
    {
      "fact": "answers.q2",
      "operator": "contains_all",
      "value": ["a2", "a4"]
    }
  ]
}
```

#### Grouped OR

```json
{
  "any": [
    {
      "fact": "answers.q1",
      "operator": "equals",
      "value": "a1"
    },
    {
      "fact": "answers.q1",
      "operator": "equals",
      "value": "a2"
    }
  ]
}
```

#### NOT

```json
{
  "not": {
    "fact": "answers.q5",
    "operator": "is_answered"
  }
}
```

### Supported facts

For v1, facts use:

```text
answers.<question_key>
```

Examples:

- `answers.q1`
- `answers.q2`
- `answers.q_favourite_colour`

### Supported operators

- `equals`
- `not_equals`
- `is_answered`
- `is_empty`
- `contains`
- `contains_any`
- `contains_all`
- `gt`
- `gte`
- `lt`
- `lte`
- `between`

### Effects shape

```json
{
  "visible": false,
  "required": false,
  "disabled": true
}
```

Supported effect keys:

- `visible`
- `required`
- `disabled`

### Constraints

- `rule_schema` must be a JSON object.
- Required top-level keys are:
  - `target`
  - `condition`
  - `effects`
- Optional top-level key:
  - `sort_order`
- `target` must be a non-empty string.
- `condition` must be an object.
- `effects` must be an object.
- `sort_order`, if present, must be numeric.
- Recursive condition validation belongs mainly in the app layer, not deep SQL checks.
- Effects should contain only supported v1 effect keys.
- Current conflict rule: evaluate matching rules in ascending `sort_order`; later matching rules override earlier ones for the effect keys they set.
- If `sort_order` is omitted, treat it as `0`.

---

## 4. Scoring

### Status

Defined for v1.

### Intended create request body wrapper

```json
{
  "scoring_key": "score_q_satisfaction",
  "scoring_schema": {
    "target": "q_satisfaction",
    "bucket": "total",
    "condition": null,
    "strategy": "rating_direct",
    "config": {
      "multiplier": 1
    }
  }
}
```

### Scoring shape

Each scoring rule follows this shape:

```json
{
  "target": "q_satisfaction",
  "bucket": "total",
  "condition": null,
  "strategy": "rating_direct",
  "config": {}
}
```

Fields:

- `target`: the question key being scored
- `bucket`: the score bucket this rule contributes to, such as `total` or `risk`
- `condition`: optional extra condition using the same condition shape as normal rules; if false, the scoring rule contributes nothing
- `strategy`: the scoring method used for the target question
- `config`: strategy-specific scoring configuration

### Recommended v1 strategies

#### Choice: `choice_option_map`

```json
{
  "target": "q_favourite_colour",
  "bucket": "total",
  "condition": null,
  "strategy": "choice_option_map",
  "config": {
    "option_scores": {
      "a1": 0,
      "a2": 2,
      "a3": 5
    },
    "combine": "sum"
  }
}
```

Notes:

- Reads `answer_value.selected`
- Maps selected option IDs to points
- `combine` should be `sum` or `max` in v1

#### Matching: `matching_answer_key`

```json
{
  "target": "q_match_capitals",
  "bucket": "total",
  "condition": null,
  "strategy": "matching_answer_key",
  "config": {
    "correct_pairs": [
      { "left_id": "c1", "right_id": "r1" },
      { "left_id": "c2", "right_id": "r2" }
    ],
    "points_per_correct": 1,
    "penalty_per_incorrect": 0,
    "max_score": 2
  }
}
```

Notes:

- Reads `answer_value.matches`
- Compares submitted matches to `correct_pairs`
- Awards points per correct pair
- May apply penalty and max score

#### Rating: `rating_direct`

```json
{
  "target": "q_satisfaction",
  "bucket": "total",
  "condition": null,
  "strategy": "rating_direct",
  "config": {
    "multiplier": 1
  }
}
```

Notes:

- Reads `answer_value.value`
- Multiplies the rating by `multiplier`

#### Field: `field_numeric_ranges`

```json
{
  "target": "q_years_experience",
  "bucket": "total",
  "condition": null,
  "strategy": "field_numeric_ranges",
  "config": {
    "ranges": [
      { "min": 0, "max": 1, "score": 1 },
      { "min": 2, "max": 5, "score": 3 },
      { "min": 6, "max": 100, "score": 5 }
    ]
  }
}
```

Notes:

- Intended only for numeric field questions in v1
- Reads `answer_value.value`
- Matches the value against configured ranges
- Returns the score for the matching range

### Constraints

- `scoring_schema` should be a JSON object
- Required top-level keys:
  - `target`
  - `bucket`
  - `strategy`
  - `config`
- Optional top-level key:
  - `condition`
- `target` should reference a valid question key
- `bucket` is a string label for score grouping
- `strategy` must be one of the supported v1 strategies
- `config` must match the selected strategy
- `condition`, if present, should use the same condition shape as rules
- Scoring is backend-calculated
- Scoring rules contribute points only; they do not change survey behaviour

### Notes

- Keep scoring simpler than normal rules
- Reuse the current question families and answer payload shapes
- Avoid arbitrary formulas in v1
- Avoid frontend-calculated scoring in v1
- Keep evaluation deterministic and easy to debug

---

## Summary

### Create question request

```json
{
  "question_key": "...",
  "question_schema": {}
}
```

### Create submission request

```json
{
  "is_anonymous": false,
  "started_at": null,
  "submitted_at": null,
  "answers": [],
  "metadata": {}
}
```

### Create rule request

```json
{
  "rule_key": "...",
  "rule_schema": {}
}
```

### Create scoring rule request

```json
{
  "scoring_key": "...",
  "scoring_schema": {
    "target": "...",
    "bucket": "...",
    "condition": null,
    "strategy": "...",
    "config": {}
  }
}
```

This is the current v1 contract.

Questions, answers, rules, and scoring are now defined at the structure level.

Scoring strategy details are intentionally kept simple for backend evaluation.

