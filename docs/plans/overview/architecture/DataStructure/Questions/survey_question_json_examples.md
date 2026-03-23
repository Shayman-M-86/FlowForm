# Survey Question JSON Examples

## Base Structure

```json
{
  "family": "...",
  "label": "...",
  "schema": {},
  "ui": {}
}
```

---

## CHOICE

### 1. Single select (radio)

```json
{
  "family": "choice",
  "label": "What is your favourite colour?",
  "schema": {
    "options": [
      { "id": "a1", "label": "Red" },
      { "id": "a2", "label": "Blue" },
      { "id": "a3", "label": "Green" }
    ],
    "min_selected": 1,
    "max_selected": 1
  },
  "ui": {
    "style": "radio",
    "display_order": 3
  }
}
```

### 2. Multi select (checkboxes)

```json
{
  "family": "choice",
  "label": "Select all fruits you like",
  "schema": {
    "options": [
      { "id": "f1", "label": "Apple" },
      { "id": "f2", "label": "Banana" },
      { "id": "f3", "label": "Orange" },
      { "id": "f4", "label": "Mango" }
    ],
    "min_selected": 1,
    "max_selected": 3
  },
  "ui": {
    "style": "checkboxes"
  }
}
```

---

## FIELD

### 3. Email input

```json
{
  "family": "field",
  "label": "What is your email address?",
  "schema": {
    "field_type": "email"
  },
  "ui": {
    "placeholder": "name@example.com"
  }
}
```

### 4. Number input

```json
{
  "family": "field",
  "label": "How many years of experience do you have?",
  "schema": {
    "field_type": "number"
  },
  "ui": {
    "placeholder": "Enter a number"
  }
}
```

---

## MATCHING

### 5. Country → capital

```json
{
  "family": "matching",
  "label": "Match each country to its capital city",
  "schema": {
    "left_items": [
      { "id": "c1", "label": "Australia" },
      { "id": "c2", "label": "Japan" },
      { "id": "c3", "label": "France" }
    ],
    "right_items": [
      { "id": "r1", "label": "Canberra" },
      { "id": "r2", "label": "Tokyo" },
      { "id": "r3", "label": "Paris" }
    ]
  },
  "ui": {
    "style": "drag_match"
  }
}
```

### 6. Term → definition

```json
{
  "family": "matching",
  "label": "Match each term to its definition",
  "schema": {
    "left_items": [
      { "id": "t1", "label": "API" },
      { "id": "t2", "label": "Database" },
      { "id": "t3", "label": "Server" }
    ],
    "right_items": [
      { "id": "d1", "label": "Stores structured data" },
      { "id": "d2", "label": "Handles requests from clients" },
      { "id": "d3", "label": "Interface for communication between systems" }
    ]
  },
  "ui": {
    "style": "drag_match"
  }
}
```

---

## RATING

### 7. 1–5 satisfaction scale

```json
{
  "family": "rating",
  "label": "How satisfied are you with our service?",
  "schema": {
    "min": 1,
    "max": 5
  },
  "ui": {
    "style": "pills"
  }
}
```

### 8. 1–10 recommendation scale

```json
{
  "family": "rating",
  "label": "How likely are you to recommend us?",
  "schema": {
    "min": 1,
    "max": 10
  },
  "ui": {
    "style": "slider"
  }
}
```

---

## Notes

- `family` controls logic grouping
- `schema` defines structure and rules
- `ui` defines presentation only
- Keep validation logic in backend, not duplicated in JSON
