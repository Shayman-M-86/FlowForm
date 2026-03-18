# FlowForm — Rule Engine Plan

## Purpose

The FlowForm Rule Engine controls dynamic behaviour in questionnaires, surveys, and quizzes. It allows a form to react to user answers using configurable logic rather than hard‑coded application code.

Rules define how a form changes while it is being completed, such as showing questions, skipping sections, assigning scores, or ending the form early.

The engine evaluates **structured rule definitions** stored as JSON against the current user session state.

---

# Goals

The rule engine should:

- Support **dynamic branching questionnaires**
- Allow behaviour to be defined through **structured JSON rules**
- Start with a **limited, predictable rule set**
- Be easy to extend in later versions
- Work for **surveys, quizzes, and decision forms**

---

# Core Concept

Each rule follows a simple pattern:

```
Trigger → Condition → Action
```

Example:

```
When Q1 is answered
If Q1 = "Yes"
Then show Q2
```

Rules operate on the **current form session state**.

---

# Key Components

## Form Definition

A form contains:

- metadata
- questions
- rule definitions

```
Form
 ├── Questions
 └── Rules
```

---

## Session State

Represents the user's current progress.

Example state:

```
answers
visible_questions
required_questions
variables
current_question
status
```

Rules read and update this state.

---

# Rule Structure

Rules are stored as JSON objects.

Example:

```json
{
  "id": "rule_show_q2",
  "trigger": "on_answer",
  "when": {
    "fact": "answers.q1",
    "operator": "equals",
    "value": "yes"
  },
  "then": [
    {"action": "show_question", "target": "q2"}
  ]
}
```

---

# Rule Execution

Typical flow:

1. User answers a question
2. Session state updates
3. Rules with matching trigger are selected
4. Conditions are evaluated
5. Matching rules execute actions
6. Session state is updated

---

# Triggers (Initial)

| Trigger | Description |
|-------|-------|
| on_answer | Fired when a question is answered |
| on_submit | Fired when the form is submitted |

---

# Conditions (Initial Operators)

| Operator | Meaning |
|--------|--------|
| equals | Exact match |
| not_equals | Not equal |
| contains | For multi‑select values |
| gt | Greater than |
| gte | Greater than or equal |
| lt | Less than |
| lte | Less than or equal |
| is_answered | Question has a value |
| is_empty | Question has no value |

### Condition Groups

Rules may combine conditions using:

- **all** (AND)
- **any** (OR)
- **not** (NOT)

Example:

```json
{
  "all": [
    {"fact": "answers.q1", "operator": "equals", "value": "b"},
    {"fact": "answers.q2", "operator": "equals", "value": "b"}
  ]
}
```

---

# Actions (Initial Set)

### Visibility

- show_question
- hide_question

### Validation

- require_question
- optional_question

### Navigation

- jump_to_question
- end_form

### Data

- clear_answer
- set_variable

### Quiz

- add_score

---

# Example Rules

### Branching

```
If Q1 == "yes"
Show Q2
```

### Conditional skip

```
If Q1 == "yes" AND Q2 == "electric"
Jump to Q5
```

### Quiz scoring

```
If Q3 == "correct"
Add score
```

### Screening

```
If Q1 == "No"
End form
```

---

# Rule Priority

Rules may optionally include a priority.

Higher priority rules override lower priority rules.

```
priority: 100
```

If no priority exists, rules run in order.

---

# Basic Evaluation Logic

Conceptual engine flow:

```
for rule in rules:
    if rule.trigger == event:
        if evaluate(rule.condition):
            apply(rule.actions)
```

---

# Data Storage

Suggested storage structure:

| Entity | Storage |
|------|------|
| forms | relational table |
| questions | relational table |
| rules | JSON / JSONB |

Rules remain flexible while questions stay structured.

---

# Future Enhancements

Possible future improvements:

- section/page navigation
- computed fields
- result routing
- rule debugging tools
- visual rule builder

---

# Summary

The FlowForm Rule Engine enables dynamic form behaviour through **declarative rules**.

Rules follow the structure:

```
trigger → condition → action
```

The first version intentionally supports a **small set of triggers, conditions, and actions** to keep the system simple, predictable, and easy to expand.
