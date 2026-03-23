# Response JSON Data Model Notes

## Purpose

Define the structure of raw answer payloads stored in `answer_value`.

---

## Structure

Each answer is stored as a database row with:

- `question_key`
- `family`
- `answer_value`

The JSON stored in `answer_value` contains only the response payload.

---

## Answer Value Structure

### CHOICE

```json
{
  "selected": ["option_id"]
}
```

---

### FIELD

```json
{
  "value": "string | number"
}
```

---

### MATCHING

```json
{
  "matches": [
    { "left_id": "string", "right_id": "string" }
  ]
}
```

---

### RATING

```json
{
  "value": number
}
```

---

## Behaviour

- `family` determines how `answer_value` is interpreted
- `question_key` links the row to the survey definition
- `answer_value` contains only user input

---

## Constraints

- `answer_value` must match the structure for the given `family`
- IDs must match values defined in the question schema
- No duplicated metadata inside `answer_value`

---

## Summary

- `answer_value` is a minimal payload
- Structure depends on `family`
- All metadata is stored outside the JSON

