# Survey Response JSON Structure

This document defines the **raw JSON payload** stored in `submission_answers.answer_value`.

Database columns such as `question_key`, `family`, and metadata now live **outside** this JSON.

The JSON here is **only** the per-family answer payload, whose shape depends on the question's **family**.

---

# General Shape

The stored JSON is **directly** one of the family-specific payloads below — there is **no wrapper object** with `question_key`, `family`, or `answer_value`.

---

# 1. CHOICE

Used for:
- single select
- multi select

```json
{
  "selected": ["option_id"]
}
```

Notes:
- Always an array
- Single select = one item
- Multi select = multiple items
- Values must match `schema.options[].id`

---

# 2. FIELD

Used for:
- text
- email
- number
- date

```json
{
  "value": "string | number | date"
}
```

Notes:
- Type depends on `schema.field_type`
- No extra metadata stored

---

# 3. MATCHING

Used for:
- pairing left items to right items

```json
{
  "matches": [
    { "left_id": "string", "right_id": "string" }
  ]
}
```

Notes:
- IDs must match `schema.left_items[].id` and `schema.right_items[].id`
- One entry per matched pair

---

# 4. RATING

Used for:
- scales
- sliders

```json
{
  "value": number
}
```

Notes:
- Must fall within `schema.min` and `schema.max`

---

# Design Rules

1. Do not store question labels or config
2. Only store user-provided values
3. Always reference IDs from the question schema
4. Keep payload minimal and consistent
5. Family determines structure — never mix formats
6. Do not duplicate `question_key` or `family` inside the JSON

---

# Summary

| Family   | Structure               |
| -------- | ----------------------- |
| CHOICE   | `{ "selected": [...] }` |
| FIELD    | `{ "value": ... }`      |
| MATCHING | `{ "matches": [...] }`  |
| RATING   | `{ "value": number }`   |

---

This structure ensures:
- consistency across all surveys
- flexibility for dynamic schemas
- clean separation between database schema (keys, families, metadata) and raw response payload

