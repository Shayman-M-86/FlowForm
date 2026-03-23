# Survey Question Model Notes

## Purpose

Defines how survey questions are structured using a shared JSON model with families.

---

## Structure

### Table: `survey_questions`

- `id`
- `survey_id`
- `question_key`
- `question_schema` (JSONB)
- `created_at`
- `updated_at`
- `deleted_at`

### JSON: `question_schema`

- `family`
- `label`
- `schema`
- `ui`

---

## Behaviour

- The application reads `question_schema` to render questions.
- `family` determines how the question is interpreted.
- `schema` defines data structure and validation rules.
- `ui` defines presentation details.

### Families

#### `choice`
- Represents selectable options.
- `schema` defines options and selection limits.

#### `field`
- Represents user input fields.
- `schema` defines the input type.

#### `matching`
- Represents paired relationships.
- `schema` defines two sets of items to match.

#### `rating`
- Represents numeric scales.
- `schema` defines minimum and maximum values.

---

## Constraints

- `question_key` must be unique per survey.
- `question_schema` must include `family`, `label`, `schema`, and `ui`.
- `family` determines allowed fields inside `schema`.

---

## Summary

Questions are stored as JSON in `question_schema`.

Families group questions by behaviour while allowing flexible configuration.

