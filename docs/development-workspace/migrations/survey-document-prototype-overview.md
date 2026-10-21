---
title: Survey document prototype overview
aliases: ["Survey document prototype overview"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-10-21
tags: [frontend]
related_code: []
related_docs:
  - "Engineering migrations"
  - "Survey builder and form-filler migration manifest"
---

# Survey document prototype overview

A browser-only design prototype exploring what FlowForm could feel like if surveys
were authored as **interactive documents** rather than as lists of database fields,
configuration screens, or workflow graphs.

> Imported from `/home/shayman86/my-repos/Test-suite/README.md` on
> 2026-10-21. The source wording is preserved apart from the page title and link
> formatting. This is prototype and migration material, not a description of
> completed FlowForm functionality. Source-relative paths and commands refer to
> the `Test-suite` checkout unless explicitly identified as FlowForm paths.
> Prototype source-file links are retained as code references. Validation results
> and dated implementation anchors below belong to the source snapshot; they
> were not rerun or refreshed for this import. FlowForm's backend document-model
> migration has since started, while the frontend integration remains unfinished.

This is a design sketch, not a production implementation. It runs entirely in the
browser with no backend, no database, and no accounts.

The reusable builder and filler are now isolated behind a portable public API.
See [[survey-builder-and-form-filler-migration|FLOWFORM-MIGRATION.md]] for the canonical move plan,
file manifest, target integration seams, and validation gates.

## What it demonstrates

- Composing a survey as a document — sections holding ordered content, edited in place
- Answer interactions configured separately from what the answer actually stores
- Conditional visibility expressed as a sentence rather than an expression language
- The same definition rendered as a real respondent survey, on desktop and mobile
- A field-shaped response kept strictly separate from the document-shaped definition
- Incremental per-answer saving, with a revision counter on every answer

## Running it

```bash
npm install
npm run dev     # http://localhost:5173
npm run build   # type-checks and builds; completes without TypeScript errors
```

## The three screens

**Builder** — a three-region layout: document outline, editing canvas, inspector.
The canvas is a document surface, not a dashboard: unselected content carries no
card or border. Hovering between items reveals a `──── + ────` insertion control;
selecting content reveals its type label and contextual actions.

The inspector splits interactive content into three tabs, mirroring the model:

| Tab | Answers the question |
| --- | --- |
| Content | What does the respondent read? |
| Answer | How is it entered, and what does it store? |
| Behaviour | When does it apply, and what makes it valid? |

**Respondent preview** — desktop shows every visible section as one continuous
document. Mobile shows one section at a time in a phone-width frame, with its own
step progress and back/continue navigation. It is a different sequencing of the
same renderer, not a shrunken desktop layout.

**Data inspector** — a drawer with three views: the live survey definition, the live
response, and a table of answer revisions. It updates as you type.

## Data-model decisions

**Interaction is not a question class.** There is no `RatingQuestion` type. A rating
is an interaction that produces a bounded integer; its presentation (numbers, stars,
faces) is a separate setting. Switching a single choice between radios, pills, cards
and a dropdown never changes what is stored. See `src/model/survey.ts`.

**The response contract is explicit and redundant.** Every field states its
`response.type` even though it could be inferred from the interaction. That
redundancy is deliberate: it shows how a future server could validate a submission
without knowing anything about how the question was rendered.

**Choices have identities separate from their labels.** An option has an immutable
typed ULID and an editable export key, such as
`{ id: "option_01K10000000000000000000001", key: "yes", label: "Yes" }`. Answers
store the ID; the key gives integrations a readable stable name. Renaming a label
cannot silently rewrite either value. The data inspector makes this visible.

**Definition and response are different objects.** The definition is document-shaped
(sections containing blocks). A response is a flat list of answer records keyed by
stable field ids — never by block position, section index, or prompt text:

```ts
{ fieldId: "field_01K10000000000000000000002", value: 12, revision: 2, committedAt: "…" }
```

Answering never mutates the definition. `commitAnswer` in
`src/model/response.ts` touches only the record it is given,
incrementing that record's revision and timestamp.

**"Block" is internal vocabulary.** It appears in the TypeScript model; the interface
says Content, Question, Answer, Behaviour, Section and Survey.

## Behaviour worth trying

1. In **Preview**, answer *"Do you currently smoke?"* with **Yes** — the cigarettes
   question appears. Answer **No** and it disappears.
2. Edit the cigarettes answer twice, then open **Data → Answer revisions**: that row
   reads revision 2 while the others stay at 1.
3. Switch the smoking question's presentation between cards, pills and a dropdown on
   the **Answer** tab. The stored value stays a choice id.
4. Submit with required questions blank to see validation, then refresh the page —
   both the edits and the answers are still there.

**Hidden answers are kept, not cleared.** If a question becomes invisible, its answer
is retained internally rather than deleted, so a respondent who changes their mind
twice does not lose earlier work. Hidden fields are excluded from validation and from
progress. The revisions table labels these rows *"hidden, answer kept"*. A production
system would need an explicit policy here; the prototype makes the behaviour visible
rather than silently deciding.

## Prototype limitations

- **Local storage is not secure and is not a database.** It is used only to simulate
  persistence so a refresh does not lose work. The app degrades to an in-memory
  session if storage is unavailable, and reports that in the top bar.
- **Advanced content types** — file upload, matrix, ranking, repeating group and
  signature — appear in the Add Content menu as clearly disabled "Coming soon"
  entries. They are listed to show where they would live, and deliberately do not
  pretend to work.
- **Images** are placeholders; there is no uploading.
- **Reordering** uses keyboard-accessible move up/down controls in the outline and on
  selected content, rather than drag-and-drop. Moving content past a section boundary
  carries it into the neighbouring section.
- **Undo/redo** covers survey-definition edits only. Respondent answers are
  deliberately not in that history, and the stack is bounded at 50 entries.
- **Validation** is illustrative, not production-grade (for example, the email check
  is a simple pattern).
- **Global workflow rules** are modelled in the type system and seeded as one disabled
  example rule, but no workflow editor is built. Local conditional visibility — the
  part that matters for this exploration — is fully implemented.
- Conditions may only reference questions appearing **earlier** in the document, which
  keeps them acyclic by construction.

## Project layout

```text
src/
├── builder/         public SurveyBuilder composition
├── filler/          public FormFiller and purpose-built response controls
├── components/
│   ├── builder/     outline, canvas, content items, Add Content menu
│   ├── inspector/   portable Content/Answer/Behaviour panels
│   ├── shared/      common primitives, overlays, hooks, and class helpers
│   └── topbar/      individually composable builder top-bar controls
├── contracts/       narrow builder/filler controller and action boundaries
├── model/           contained temporary survey and response model
├── styles/          portable styles, demo theme, and demo document shell
├── demo/            mock data, local persistence, reducer, chrome, inspector
├── index.ts         portable public exports; deliberately excludes demo code
└── utils/           portable ids and validation helpers
```

The demo state is a single `useDemoStore` hook over a reducer — no state library.
Portable visual components receive only the narrow controller contracts in
`src/contracts`; they do not import the demo store, mock survey, local storage,
project chrome, or data inspector.

## Related documents

- [[migrations-index|Engineering migrations]]
- [[survey-builder-and-form-filler-migration|Survey builder and form-filler migration manifest]]
