# AI Documentation Notes Structure

## Purpose

This document defines how to write short, structured notes that can later be used by an AI model to generate clear and accurate documentation.

The goal is to:

- avoid missing important details
- avoid overfitting to one explanation style
- prevent the AI from making assumptions or inventing details

---

## Core Principles

### 1. Be factual, not descriptive
Write what the system does, not why it is good or how it feels.

Avoid:
- opinions
- marketing language
- unnecessary explanation

---

### 2. Keep statements atomic
Each line or bullet should express one idea.

Good:
- "Questions are stored as JSON in `question_schema`."

Avoid:
- long paragraphs mixing multiple ideas

---

### 3. Use consistent terminology
Always use the same names for the same concepts.

Examples:
- `survey`
- `survey_questions`
- `question_schema`
- `survey_rules`

Do not switch between synonyms.

---

### 4. Do not imply behaviour
Only document behaviour that is explicitly defined.

Avoid:
- guessing edge cases
- assuming defaults unless specified

---

### 5. Separate structure from behaviour
Clearly distinguish between:

- data structure (tables, JSON shape)
- runtime behaviour (how the app evaluates or processes data)

---

## Recommended Format

Each note document should follow this structure:

### Title
Short and specific.

### Purpose
One or two sentences describing what the component is.

### Structure
Describe the data shape:
- tables
- fields
- JSON structure

### Behaviour
Describe what the system does with the data.

### Constraints (optional)
List rules or limitations.

---

## Writing Style

- Use short sentences
- Prefer bullet points over paragraphs
- Avoid repetition
- Avoid examples unless necessary for clarity

---

## What to Avoid

- large combined explanations
- speculative features
- implementation details not yet decided
- mixing multiple components in one document

---

## Summary

These notes are not final documentation.

They are structured inputs for an AI model.

The goal is to provide:

- clear facts
- consistent structure
- minimal ambiguity

So the AI can later generate complete, accurate documentation without inventing details.

