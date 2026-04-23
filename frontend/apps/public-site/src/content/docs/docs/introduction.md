---
title: Introduction
description: What FlowForm is, how it works, and what you can build with it.
---

FlowForm is a **security-first form and survey builder**. You design your questions visually in the browser — no code required — and the builder outputs a clean, structured JSON schema you can send to any backend or API.

## What makes FlowForm different?

Most form builders are wrappers around simple input fields. FlowForm is built around a **flow model** — each question is a node, and nodes can have rules attached that control the path a respondent takes through the form.

- **Five question types** — multiple choice, matching, rating, open-field, and logic rules
- **Visual rule builder** — set branching and skip logic without writing code
- **Pseudonymous by design** — response data is never stored alongside real user identities
- **Dual-database isolation** — form structure and raw responses live in completely separate databases

## How it works

1. Open the builder on the [home page](/) and add your questions
2. Use the **Rules** node type to add conditional branching between questions
3. Hit **Preview form** to test the respondent experience end-to-end
4. When you're happy, export the JSON schema and send it to your backend

## Architecture overview

```
Builder (browser)
  └─ Produces a SurveyNode[] JSON schema

Backend (Flask)
  ├─ core DB   — survey structure, metadata, submission registry
  └─ response DB — raw answer data, pseudonymous subject IDs
```

```json
{
  "type": "question",
  "sort_key": 100000, 
  "content": {
    "id": "q1",
    "title": "Satisfaction Survey",
    "label": "How satisfied are you?",
    "family": "rating",
    "definition": {
      "variant": "slider",
      "range": {
        "min": -5,
        "max": 5,
        "step": 1
      },
      "ui": {
        "left_label": "Not satisfied",
        "right_label": "Very satisfied"
      }
    }
  }
}
```

The two databases share a single integer key (`core_submission_id`) but have no cross-database foreign keys. This means response data can be backed up, retained, or deleted completely independently of the survey structure.

## Next steps

- [Building Your First Form](/docs/building-your-first-form) — a step-by-step walkthrough
- [Question Types](/docs/question-types/overview) — every node type explained
