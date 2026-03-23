# Survey Response Examples

## Base Structure

The stored JSON is **only** the raw family-specific payload. There is **no wrapper** with `question_key`, `family`, or `answer_value`.

---

## CHOICE

### 1. Single select (radio)

```json
{
  "selected": ["a2"]
}
```

### 2. Multi select (checkboxes)

```json
{
  "selected": ["f1", "f3", "f4"]
}
```

---

## FIELD

### 3. Email input

```json
{
  "value": "name@example.com"
}
```

### 4. Number input

```json
{
  "value": 6
}
```

---

## MATCHING

### 5. Country → capital

```json
{
  "matches": [
    { "left_id": "c1", "right_id": "r1" },
    { "left_id": "c2", "right_id": "r2" },
    { "left_id": "c3", "right_id": "r3" }
  ]
}
```

### 6. Term → definition

```json
{
  "matches": [
    { "left_id": "t1", "right_id": "d3" },
    { "left_id": "t2", "right_id": "d1" },
    { "left_id": "t3", "right_id": "d2" }
  ]
}
```

---

## RATING

### 7. 1–5 satisfaction scale

```json
{
  "value": 4
}
```

### 8. 1–10 recommendation scale

```json
{
  "value": 9
}
```

