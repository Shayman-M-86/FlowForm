# Frontend deduplication audit (Studio-focused)

## Scope reviewed
- `frontend/packages/builder` (Studio app / question builder + form filler)
- `frontend/packages/ui` (shared UI primitives)
- `frontend/packages/styles` / shared class conventions where relevant

---

## High-impact duplication opportunities

## 1) Repeated “question card shell” logic across node components

### Where this repeats
`FieldQuestion`, `MultiChoiceQuestion`, `MatchingQuestion`, and `RatingQuestion` all re-implement the same skeleton:
- Local state for `title`, `label`, `id`, `required`
- `NodePillCollapsed` rendering branch
- `NodePillTopbar` wiring + settings payload
- `NodePillQuestionField` block
- `toggleEditMode` boilerplate
- `useImperativeHandle` + `onDataChange` push pattern

### Why this matters
This drives a lot of line count and forces every question type change (e.g., ID validation behavior, topbar UX, collapsed summary behavior) to be repeated across files.

### Standardisation proposal
Create a shared `useQuestionCardState` hook and/or a `QuestionCardFrame` component:
- Hook handles common state and emits base data (`id`, `title`, `label`, `required`).
- Frame renders collapsed/edit shell + topbar + question field.
- Individual question components only render “definition-specific controls” (field type, options, slider config, etc.).

### Estimated impact
- Medium/high reduction in LOC in each node component.
- Lower risk for inconsistent behavior between question families.

---

## 2) Option-list editing logic duplicated in multi-choice + matching

### Where this repeats
`MultiChoiceQuestion` and `MatchingQuestion` share near-identical list-editing behavior:
- Add/remove/reorder items
- Open/close per-item detail state with `Set`
- Character budget calculations
- Repeated usage of `useOptionDrag`
- Repeated option row CSS class stacks

### Why this matters
Any improvements to option editing UX currently need parallel implementation.

### Standardisation proposal
Extract a reusable `EditableOptionList` primitive with config-driven behavior:
- `items`, `setItems`, `maxItems`, `poolLimit`, `perItemLimit`, `labels`
- Optional two-column mode for matching (left/right list)
- Shared row renderer that supports drag handle + inline metadata + expandable text area

### Estimated impact
- Significant LOC reduction in `MatchingQuestion` and `MultiChoiceQuestion`.
- Better UX consistency for drag/reorder and constraints.

---

## 3) Form-filler wrappers duplicate section headers/layout patterns

### Where this repeats
`FieldFormFiller`, `MultiChoiceFormFiller`, `MatchingFormFiller`, and `RatingFormFiller` each rebuild similar:
- Section wrappers (`flex flex-col gap-*`)
- Label + helper header rows
- Bordered preview cards and muted surfaces

### Why this matters
Minor but persistent CSS duplication; style shifts are costly.

### Standardisation proposal
Introduce a small set of builder-specific presentation primitives in `packages/ui` (or builder-local `shared`):
- `QuestionSection`
- `QuestionMetaHeader`
- `PreviewPanel`
- `CountBadge`

These can still accept `className` overrides for variant-specific visuals.

### Estimated impact
- Moderate LOC reduction in form-filler files.
- Faster theme/styling alignment.

---

## 4) Two overlapping auto-resizing textarea components in UI package

### Where this repeats
- `LargeInput` provides textarea behavior + auto-grow + labels/hints/errors.
- `ExpandableTextArea` separately implements auto-resize shell.
- `ExpandableSelector` again implements similar textarea resize pattern.

### Why this matters
Three implementations for overlapping text-area concerns increases maintenance cost and creates subtle behavior drift.

### Standardisation proposal
Consolidate around a single low-level `AutoResizeTextarea` primitive and layer wrappers:
- Base primitive: resize behavior + min/max constraints + textarea classes
- Wrappers:
  - `LargeInput` for form-labeled use cases
  - `ExpandableTextArea` for shell-based card use cases
  - `ExpandableSelector` for selectable rows

### Estimated impact
- Medium LOC reduction in UI package.
- Better behavior consistency and fewer resize bugs.

---

## 5) Repeated inline class strings suitable for semantic tokens/util classes

### Where this repeats
Frequent reuse of utility bundles like:
- `text-[0.78rem] font-semibold uppercase tracking-[0.04em] text-muted-foreground`
- Repeated rounded border-muted panel styles (`rounded-2xl border border-border bg-muted/10 ...`)
- Repeated min-height textarea classes (`min-h-[46px]`, `max-h-[90px|170px|200px]`)

### Why this matters
Large JSX class strings inflate component size and reduce readability.

### Standardisation proposal
Move common class bundles into either:
- shared exported constants (as already done in `nodePillStyles.ts`), or
- component-level variants with `cva`/variant maps in `packages/ui`.

Start with the most repeated blocks in form fillers and rating/matching previews.

### Estimated impact
- Small/moderate raw LOC reduction.
- Larger readability and maintainability gain.

---

## 6) Duplicate choice-selection semantics between builder + filler paths

### Where this repeats
Selection constraints (`min/max`, single vs multi behavior, disable when at max) are implemented in form filler logic and similarly implied in node editor configuration.

### Why this matters
Rules can diverge over time (preview behaves differently from runtime).

### Standardisation proposal
Extract pure helpers in a shared module (`packages/builder/src/lib/choiceRules.ts`):
- `isSingleSelect(definition)`
- `canToggleOption(...)`
- `toggleOptionSelection(...)`

Use the same helpers for preview and filler paths where possible.

### Estimated impact
- Small LOC reduction, high correctness improvement.

---

## 7) Rating variant rendering can be split into dedicated subcomponents

### Where this repeats
`RatingFormFiller` has a large switch for `slider`, `emoji`, and `star` with repeated wrapper/panel/labels scaffolding.

### Why this matters
Single large file is harder to reason about and contributes to class duplication.

### Standardisation proposal
Split into:
- `RatingSliderFiller`
- `RatingEmojiFiller`
- `RatingStarFiller`

Keep shared constants and helpers in one `ratingShared.ts` module.

### Estimated impact
- Net LOC might be neutral initially, but complexity drops and repeated wrapper patterns can then be consolidated.

---

## Quick win order (recommended)
1. Consolidate textarea primitives (`LargeInput` / `ExpandableTextArea` / `ExpandableSelector`).
2. Extract shared question card frame/state for node components.
3. Build reusable editable option-list primitive for multi-choice + matching.
4. Introduce form-filler layout primitives and class tokens.
5. Refactor rating filler into variant components.

---

## Suggested implementation checklist
- [ ] Add `QuestionCardFrame` + `useQuestionCardState` in builder shared folder.
- [ ] Migrate `FieldQuestion` first (smallest surface) as reference implementation.
- [ ] Extract `EditableOptionList` and adopt in `MultiChoiceQuestion`.
- [ ] Extend `EditableOptionList` to dual-column mode and adopt in `MatchingQuestion`.
- [ ] Create `AutoResizeTextarea` primitive in `packages/ui` and retrofit `Expandable*` + `LargeInput`.
- [ ] Add reusable filler surface/header components and migrate all filler components.
- [ ] Add tests (or Storybook examples) for shared primitives to prevent regressions.

---

## Notes on line-count reduction strategy
- Prefer extracting repeated _behavior_ first (hooks/helpers/components) over only extracting class strings.
- Avoid over-abstracting once-only differences; target patterns repeated in **2+ files**.
- Keep variants explicit via props/variant maps to avoid unreadable generic factories.
