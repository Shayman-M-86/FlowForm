---
title: Question Types Overview
description: Every node type available in the FlowForm builder.
---

FlowForm has five node types. Four are question types that collect respondent input; the fifth is a logic node that controls branching.

| Node type | Family | Use it when… |
|---|---|---|
| **Multiple choice** | `choice` | Respondents pick one option from a list |
| **Matching** | `matching` | Respondents pair items from two columns |
| **Rating** | `rating` | Respondents give a numeric or star rating |
| **Field** | `field` | You need an open-ended text or number answer |
| **Rules** | — | You want conditional branching or skip logic |

## Multiple choice

The most common question type. Each option has a label and an optional numeric score, which is useful for scored assessments or NPS-style surveys.

```json
{
  "family": "choice",
  "id": "q_satisfaction",
  "title": "How satisfied are you overall?",
  "options": [
    { "label": "Very satisfied", "score": 5 },
    { "label": "Not satisfied", "score": 1 }
  ]
}
```

## Matching

Presents two lists side by side and asks the respondent to draw connections between them. Good for knowledge checks and vocabulary exercises.

## Rating

A numeric scale question. You can configure the min, max, and step values, plus optional labels for the low and high ends of the scale.

## Field

An open-ended input — text, number, email, or date. Use it for free-text comments, names, or any answer that doesn't fit a fixed set of options.

## Rules

Rules nodes don't collect input — they evaluate conditions against previous answers and route respondents to different points in the form. See [Rules](/docs/question-types/rules) for full details.
