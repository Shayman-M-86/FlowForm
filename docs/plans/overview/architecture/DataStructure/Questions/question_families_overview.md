# Question Families Overview

Question families exist to group questions by the kind of data they collect and the way they behave.

This keeps the question model flexible without needing a different database table for every question type.

Each question still follows one shared shape:

- `family`
- `label`
- `schema`
- `ui`

The `family` tells the application what broad kind of question it is.
The `schema` holds the structural configuration for that family.
The `ui` holds presentation details for how it should be rendered.

## Why families are useful

Families make it easier to:

- organize question types into clear groups
- validate question structures in a predictable way
- render questions consistently in the frontend
- extend the system later without redesigning the database

Instead of treating every question type as completely separate, families let related question types share the same overall structure.

## How each family is configured

### Choice
Choice questions are configured with selectable options and selection rules.
Their schema describes the available options and any rules about how many may be selected.

### Field
Field questions are configured by the kind of input they accept.
Their schema describes the field type, such as text, email, number, date, or phone.

### Matching
Matching questions are configured with two related sets of items.
Their schema describes the items that should be matched together.

### Rating
Rating questions are configured with a scoring range.
Their schema describes the minimum and maximum values for the scale.

## Summary

Families provide a clean middle ground between a rigid SQL-only model and an unstructured JSON-only model.
They give the system a clear high-level question type while still allowing each family to have its own configuration rules.

