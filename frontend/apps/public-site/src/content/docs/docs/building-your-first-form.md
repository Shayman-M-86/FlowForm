---
title: Building Your First Form
description: A step-by-step guide to creating, previewing, and exporting a form in FlowForm.
---

This guide walks you through building a simple satisfaction survey from scratch in under five minutes.

## Step 1 — Open the builder

Head to the [home page](/) and scroll down to the **Live builder** section, or click **Start building now** in the hero. The builder auto-saves everything to your browser as you work — no account needed.

## Step 2 — Add a multiple choice question

Click **+ Multiple choice** in the "Add another question" panel at the bottom of the builder.

A new question node appears with default settings. Click into the node to expand it into edit mode:

- **Question ID** — a unique identifier used in the JSON schema (e.g. `question_id_1`). You can rename this to something meaningful like `overall_satisfaction`.
- **Title** — the question text respondents will see.
- **Options** — add as many choices as you need. Each option gets its own label and an optional score value.

## Step 3 — Add a follow-up field question

Click **+ Field** to add an open-ended text question below. Set its title to something like *"Any other comments?"*.

Your builder now has two nodes stacked in order.

## Step 4 — Preview the form

Click **Preview form** in the toolbar. The builder switches to the form filler view — this is exactly what a respondent would see.

Step through the form to test it. When you're done, click **Back to builder** to return.

## Step 5 — Export the schema

The builder serialises your form to JSON automatically. You can access the schema via the `flowform.node-page.schema` key in your browser's `localStorage`:

```js
JSON.parse(localStorage.getItem('flowform.node-page.schema'))
```

The output is a `SurveyNode[]` array — one entry per question or rule, each with a `sort_key`, `type`, and `content` block.

```json
[
  {
    "type": "question",
    "sort_key": 0,
    "content": {
      "family": "choice",
      "id": "overall_satisfaction",
      "title": "How satisfied are you?",
      "options": [
        { "label": "Very satisfied", "score": 5 },
        { "label": "Satisfied", "score": 4 },
        { "label": "Neutral", "score": 3 }
      ]
    }
  }
]
```

## What's next?

- Learn about all five [Question Types](/docs/question-types/overview)
- Add branching logic with [Rules nodes](/docs/question-types/rules)
