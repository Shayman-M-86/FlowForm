# Survey Rules Structure and Operators

## Purpose

This document defines a clean v1 structure for `survey_rules`.

The goal is to support declarative browser-side survey behaviour such as:

- show or hide questions
- make questions required or optional
- enable or disable questions

This model is not trigger-based. Instead, each rule describes:

- a target
- a condition
- one or more effects

The browser evaluates the rules against the current answer state while the user is filling out the survey.

---

## Core Idea

Each rule follows this shape:

```json
{
  "target": "q3",
  "condition": {
    "fact": "answers.q1",
    "operator": "equals",
    "value": "a2"
  },
  "effects": {
    "visible": false
  }
}
```

Meaning:

- this rule targets `q3`
- if the condition is true
- apply the listed effects

---

## Rule JSON Structure

### Base Shape

```json
{
  "target": "string",
  "condition": {},
  "effects": {}
}
```

### Fields

#### `target`
The question or entity the rule applies to.

Examples:

- `q2`
- `q3`
- `section_1`

For v1, targeting questions is enough.

#### `condition`
A boolean expression evaluated against current survey answers.

#### `effects`
The properties to apply when the condition evaluates to true.

---

## Condition Structure

Conditions should support both simple checks and grouped logic.

### Simple Condition

```json
{
  "fact": "answers.q1",
  "operator": "equals",
  "value": "a2"
}
```

### Grouped AND Condition

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

### Grouped OR Condition

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

### NOT Condition

```json
{
  "not": {
    "fact": "answers.q5",
    "operator": "is_answered"
  }
}
```

### Nested Condition Example

```json
{
  "all": [
    {
      "fact": "answers.q1",
      "operator": "equals",
      "value": "yes"
    },
    {
      "any": [
        {
          "fact": "answers.q2",
          "operator": "equals",
          "value": "a"
        },
        {
          "fact": "answers.q2",
          "operator": "equals",
          "value": "b"
        }
      ]
    }
  ]
}
```

---

## Supported Facts

Facts reference the current survey state.

For v1, the main fact format should be:

```text
answers.<question_key>
```

Examples:

- `answers.q1`
- `answers.q2`
- `answers.q_favourite_colour`

This keeps the system simple and tied to question keys.

---

## Operators

Operators should be chosen based on the shape of the answer value.

### General Operators

#### `equals`
True if the answer exactly matches the value.

Example:

```json
{
  "fact": "answers.q1",
  "operator": "equals",
  "value": "a2"
}
```

#### `not_equals`
True if the answer does not exactly match the value.

#### `is_answered`
True if the answer exists and is not empty.

Example:

```json
{
  "fact": "answers.q4",
  "operator": "is_answered"
}
```

#### `is_empty`
True if the answer does not exist or is empty.

---

### Multi-Select Operators

#### `contains`
True if the answer array contains a single value.

Example:

```json
{
  "fact": "answers.q2",
  "operator": "contains",
  "value": "a2"
}
```

#### `contains_any`
True if the answer array contains at least one of the listed values.

Example:

```json
{
  "fact": "answers.q2",
  "operator": "contains_any",
  "value": ["a2", "a4"]
}
```

#### `contains_all`
True if the answer array contains all listed values.

Example:

```json
{
  "fact": "answers.q2",
  "operator": "contains_all",
  "value": ["a2", "a4"]
}
```

---

### Numeric Operators

Useful for number and rating questions.

#### `gt`
Greater than.

#### `gte`
Greater than or equal.

#### `lt`
Less than.

#### `lte`
Less than or equal.

#### `between`
True if a value falls within a range.

Example:

```json
{
  "fact": "answers.q7",
  "operator": "between",
  "value": [3, 5]
}
```

---

## Effects Structure

Effects define what changes when the condition is true.

### Base Shape

```json
{
  "visible": false,
  "required": false
}
```

### Recommended v1 Effects

#### `visible`
Boolean.
Controls whether the target question is shown.

#### `required`
Boolean.
Controls whether the target question must be answered.

#### `disabled`
Boolean.
Controls whether the target question can be interacted with.

---

## Example Rules

### Show a question when a previous answer is yes

```json
{
  "target": "q2",
  "condition": {
    "fact": "answers.q1",
    "operator": "equals",
    "value": "yes"
  },
  "effects": {
    "visible": true
  }
}
```

### Hide a question when a previous answer is no

```json
{
  "target": "q2",
  "condition": {
    "fact": "answers.q1",
    "operator": "equals",
    "value": "no"
  },
  "effects": {
    "visible": false
  }
}
```

### Require a question only if another question has been answered

```json
{
  "target": "q5",
  "condition": {
    "fact": "answers.q4",
    "operator": "is_answered"
  },
  "effects": {
    "required": true
  }
}
```

### Multi-condition rule

```json
{
  "target": "q3",
  "condition": {
    "all": [
      {
        "fact": "answers.q1",
        "operator": "equals",
        "value": "answer_2"
      },
      {
        "fact": "answers.q2",
        "operator": "contains_all",
        "value": ["answer_2", "answer_4"]
      }
    ]
  },
  "effects": {
    "visible": false
  }
}
```

### Numeric threshold rule

```json
{
  "target": "q10",
  "condition": {
    "fact": "answers.q9",
    "operator": "gte",
    "value": 18
  },
  "effects": {
    "visible": true
  }
}
```

---

## Default Behaviour

A rule only applies its effects when its condition is true.

When the condition is false, the rule does nothing.

That means the survey should still have base defaults defined in the question JSON or the form renderer.

Examples:

- questions may be visible by default
- questions may be optional by default
- rules override those defaults only when matched

---

## Suggested SQL Table

```sql
CREATE TABLE survey_rules (
    id BIGSERIAL PRIMARY KEY,
    survey_id BIGINT NOT NULL REFERENCES surveys(id) ON DELETE CASCADE,
    rule_key TEXT NOT NULL,
    rule_schema JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE (survey_id, rule_key)
);
```

---

## Recommended v1 Scope

For v1, support only:

### Condition groups
- simple condition
- `all`
- `any`
- `not`

### Operators
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

### Effects
- `visible`
- `required`
- `disabled`

This is enough to support a lot of dynamic form logic without making the system too big too early.

---

## Summary

The survey rule model should be declarative, browser-evaluated, and based on:

- `target`
- `condition`
- `effects`

Conditions should support grouped logic and a small clear set of operators.

Effects should focus on UI state in v1.

This keeps the rule model flexible, understandable, and well aligned with a dynamic survey builder.

Recommended semantics

Use:

{
  "target": "q3",
  "sort_order": 20,
  "condition": { ... },
  "effects": {
    "visible": false,
    "required": true
  }
}

Then the engine does:

start from base question defaults
find matching rules for that target
sort by sort_order
merge effects
later rule overrides earlier rule only for the keys it sets

So this:

rule 1 -> { "visible": true }
rule 2 -> { "required": true }

becomes:

{ "visible": true, "required": true }

But this:

rule 1 -> { "visible": true }
rule 2 -> { "visible": false }

becomes:

{ "visible": false }
Best v1 choice

I’d use:

sort_order
last match wins
tie-breaker by rule_key if two rules have the same order