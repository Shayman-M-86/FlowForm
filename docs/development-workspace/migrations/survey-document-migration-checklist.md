---
title: Survey document migration checklist
aliases: ["Survey document migration checklist"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-10-21
tags: [backend, frontend]
related_code:
  - "../../../backend/app/schema/api/content/survey_document.py"
  - "../../../infra/database/init/schema/flowform_core_db_schema_v4.sql"
  - "../../../backend/app/services/surveys.py"
  - "../../../backend/app/db/error_handling/integrity_rules.py"
  - "../../../backend/app/api/v1/studio/surveys/versions.py"
  - "../../../backend/app/api/v1/respondent/submission_sessions.py"
  - "../../../backend/app/services/admin_results/core/session_tree.py"
  - "../../../frontend/apps/studio-app/src/pages/SurveyWorkspaceTabPages/useSurveyBuilderController.ts"
  - "../../../frontend/apps/studio-app/src/pages/RespondPage.tsx"
related_docs:
  - "Engineering migrations"
  - "Survey document prototype overview"
  - "Survey builder and form-filler migration manifest"
  - "Responses and encryption"
---

# Survey document migration checklist

FlowForm has substantial document-model groundwork, but the migration is
unfinished across the APIs, results, frontend, and supporting tests and data.
This checklist records the repository inspection of 2026-10-21 and the work
needed to complete that transition.

Checked items mean the implementation exists in source. They do not mean the
complete application journey or database behaviour has been verified. Open
decision items identify behaviour to settle before dependent implementation.
The imported prototype documents remain the reference for the intended
experience; their earlier validation results are not completion evidence here.

## Groundwork already implemented

- [x] Define a canonical survey document containing sections and ordered content.
- [x] Separate question content, interaction, stored response type, and behaviour.
- [x] Introduce stable field IDs as the answer identity in migrated internals.
- [x] Validate required content, supported types, interaction compatibility,
  bounds, option identities, and document size.
- [x] Add publication checks for duplicate IDs and field keys, missing references,
  incompatible conditions, missing options, and circular dependencies.
- [x] Change baseline SQL to store a complete document and revision per version,
  remove separate question/scoring tables, and use field-based slots and events.
- [x] Update the corresponding ORM models and remove old content mappings.
- [x] Rework survey loading, replacement, copying, and publication services.
- [x] Resolve and validate answers against the stored field before saving them.
- [x] Change encrypted answer payloads to identify their field, retaining the
  existing core/response storage separation.
- [x] Update integrity mappings for document locking and field-based answer slots,
  removing obsolete node/scoring mappings.
- [x] Add field-answer, missing-field, and document-publication error contracts.
- [x] Add focused document, publication, answer-validation, and crypto tests;
  update some existing tests and generated contracts.
- [x] Import the prototype overview and migration manifest into this workspace.

## 1. Settle scope and compatibility

The following direction was supplied by the project owner on 2026-10-21.
Checked decisions record agreed scope, not completed implementation.

- [x] Rebuild fresh. No existing surveys, sessions, or answers need preservation;
  no legacy-data conversion or old encrypted-payload compatibility is required.
  This records the reset decision; no data was deleted during documentation work.
- [x] Aim for a close one-to-one match with the working prototype. Older features
  absent from that prototype need not be included immediately. Per-answer
  counters/history are explicitly excluded below.
- [x] Use pragmatic backend contracts rather than enforcing every prototype detail
  as a permanent backend rule. Reconcile metadata and option keys during the
  adapter work without turning every frontend concern into server validation.
- [x] Restrict authored conditions to earlier questions. Keep the backend simple;
  do not infer that this requires a second survey-logic engine on the server.
- [x] Keep hidden-question behaviour in the frontend, following the prototype's
  retained-answer behaviour, without strict backend visibility restrictions.
  Exact result/export presentation still needs implementation-level agreement.
- [x] Keep only the latest saved answer. No per-answer revision counters or
  previous-value history are required.
- [x] Reuse and adapt FlowForm's existing completion lifecycle. The backend should
  check data shape and retain its access/session/field-ownership safeguards;
  it should not re-evaluate survey visibility and required-answer logic at
  completion. The earlier proposed backend completion validator is not required.
- [x] Reuse and adapt existing session/resume behaviour. Inspect what FlowForm
  already does before introducing replacement mechanisms. Verify the integrated
  experience rather than assuming that all answer restoration is already present
  in the current API response.
- [ ] Define concurrent-edit behaviour if needed for document saving. The response
  numbering did not clearly settle this item; no conflict-handling design has
  been approved by these decisions.
- [ ] Review existing document and per-answer validation against the agreed simple
  backend boundary. Identify which constraints concern data shape/integrity and
  which would duplicate frontend survey logic before changing validators.

### Answer slots and encrypted responses

The imported frontend migration manifest covers per-answer saving and preserves
FlowForm-owned submission/session handling. It does not specify answer slots or
redesign encryption. This section makes the existing backend path explicit.

An answer slot is a stable core-side record for one field in one respondent
session, pinned to that session's survey version. It stores identity metadata,
not the answer value. The SQL, ORM, and slot repository have already changed the
identity from question-node ID to `field_id`, with uniqueness on
`(submission_session_id, field_id)`.

```text
core session + frozen survey document
                 |
          field_id -> answer slot
                           |
                 slot ID + linkage key
                           |
                 opaque answer locator
                           |
response envelope -> current encrypted answer row
```

Session start creates a response envelope with a wrapped per-session encryption
key. Each answer save resolves the field, obtains or reuses its slot, derives an
opaque locator from the slot ID and linkage key, and encrypts the field ID,
answer state, and value using AES-256-GCM with the session key and a fresh nonce.
The response database stores ciphertext and opaque locators, without plaintext
core session, survey, or field identifiers.

Saving the same field again updates the same response-side answer row with new
ciphertext and a fresh nonce. Completion marks the core session complete; it
does not encrypt the entire filled-out survey as one document. An authorized
results read follows slots to encrypted rows, decrypts them, and combines them
with field metadata from the frozen definition. Result assembly and exports now use the frozen document field metadata.

- [x] Field-based slots and answer encryption already exist in the migrated
  backend internals; reuse that architecture for document-based surveys.
- [x] Connect the respondent routes to the existing field-based save path.
- [ ] Connect the prototype filler adapter to the migrated respondent routes.
- [x] Preserve slot identity across repeated saves and verify latest-answer
  replacement, clearing, fresh nonces, and field ownership in integration tests.
- [x] Adapt result assembly/export to field metadata from the frozen document.
- [ ] Verify existing session start/resume/completion and two-database failure
  handling through the migrated user journey.

See [[responses-and-encryption|Responses and encryption]] for the broader
storage/key model. The field-based storage and results path has also been exercised by the
backend database suite; full browser integration remains unfinished.

## 2. Finish backend APIs and results

- [x] Parse and pass the document when creating a Studio survey version.
- [x] Expose document replacement through a registered route, using the existing
  request model, service, permissions, and draft-editability checks.
- [x] Change respondent answer routes from question-node UUIDs and old answer
  envelopes to field IDs and the new request/response contracts.
- [x] Build answer responses from the server-resolved field and normalized value.
- [x] Connect event routes to field-viewed requests and service methods.
- [x] Verify public survey retrieval and start/resume responses carry the new
  definition consistently, preserving pinned-version and access behaviour.
- [x] Rebuild result metadata from the session's frozen document instead of
  removed question tables.
- [x] Update result assembly, decrypted answer interpretation, response contracts,
  and event timelines to field identity and response types.
- [x] Update CSV/JSON exports to the agreed field keys and answer values.
- [x] Restore migrated results routes to normal registration.
- [x] Retire remaining legacy node/scoring route files and contracts once their
  replacements and scope decisions are complete.

## 3. Complete error handling

- [x] Fix normalized validation paths for new document discriminators. The
  inspection reproduced `document.sections.0.blocks.0.paragraph.content.text`,
  where `paragraph` is an internal tag rather than a request property.
- [x] Cover the new discriminator paths with meaningful validation tests.
- [x] Verify the changed document-lock trigger against a real database, including
  its translated status code and message.
- [ ] Expand dedicated database-error translation coverage where gaps remain.
- [x] Exercise missing-field and invalid-answer errors through the migrated API
  routes and regenerate their contracts.
- [ ] Add dedicated HTTP coverage for publication-issue responses.
- [ ] Display document/publication issues against relevant content in Studio.
- [ ] Handle respondent save failures, pending state, and retries in the new host
  adapter so failed saves cannot appear successful.

Keep the existing global error shape and validation pipeline. The inspection
found targeted gaps, not a need to replace the error framework. Database CHECK
constraints intentionally left as server-invariant failures do not all need
client-facing integrity mappings.

## 4. Verify SQL, fixtures, and development setup

- [ ] Replace mock SQL that still inserts old compiled schemas, question/scoring
  rows, question-node events, or removed sequences.
- [ ] Review response mock data and its answer-locator/payload assumptions.
- [x] Verify fresh core and response schema bootstrap in PostgreSQL test databases.
- [x] Verify ORM mappings, renamed constraints, publication immutability, and
  field-based answer slots/events against that database.
- [ ] Rebuild fresh databases and compatible fixtures using the agreed reset
  approach; no existing-data conversion is needed.
- [ ] Verify development bootstrap/load scripts and the packaged AWS bootstrap
  inputs use the intended schema and compatible fixtures.

## 5. Regenerate contracts and integrate the frontend

- [x] Regenerate and check OpenAPI after backend route contracts are complete.
- [ ] Provide a supported generation path for document builder types and runtime
  validators. Current builder outputs are effectively empty while callers still
  import removed types.
- [x] Regenerate frontend types, constraints, and permission metadata from their
  sources; do not repair generated files by hand.
- [ ] Replace node API hooks and node-diff persistence with document operations.
- [ ] Adapt draft recovery/storage and handle any incompatible old local drafts.
- [ ] Import the portable builder and filler following the migration manifest,
  preserving FlowForm-owned theme, routing, permissions, and network lifecycle.
- [ ] Connect Studio version switching, dirty state, saving, publication, copying,
  and archiving to the new builder.
- [ ] Compose the extracted toolbar controls into FlowForm's existing chrome.
- [ ] Connect preview and real respondent routes to the document renderer and
  field-answer API, preserving resolve/start/resume/save/complete behaviour.
- [ ] Update AI-import prompts, parsing, and validation to document definitions.
- [ ] Reconcile undo/redo, restored answers, and completion behaviour with the
  decisions above; omit prototype per-answer counters/history.
- [ ] Verify light/dark themes, desktop/mobile layouts, keyboard focus, conditional
  visibility, and mobile section sequencing. Keep the phone frame preview-only.
- [ ] Remove superseded builder/filler code only after integration gates pass.

## 6. Complete verification and documentation

- [ ] Migrate legacy factories and lifecycle, session, results, export, and crypto
  tests to the agreed contracts; replace obsolete tests rather than preserving
  deleted tables through compatibility shims.
- [ ] Run focused tests and the full backend suite against real databases.
- [ ] Pass the complete Python type-check surface and relevant frontend
  type checks, builds, lint, and tests.
- [ ] Verify one complete journey: create survey → edit document → publish →
  share → answer → resume → complete → review results → export.
- [ ] Verify permissions, published-version stability, and encrypted response
  isolation remain correct through that journey.
- [ ] Update maintained product/backend documentation and public JSON examples
  that still describe the old node model.
- [ ] Record completion evidence and archive this checklist when it no longer
  governs active migration work.

## Backend route and results implementation update

The backend routes and results migration has been implemented. Studio creates
versions from definitions and replaces draft definitions through a PUT route.
Respondent saves/events use fields. Results routes are registered again, with
field-based results and exports. Obsolete node/scoring routes, content schemas,
legacy answer contracts, and their unused errors/enums have been removed.
The corresponding persistence/contract tests now use canonical definitions.

Validation for this implementation:

- Backend suite: 716 passed, 2 deselected, against fresh PostgreSQL test databases.
- All four Python type-check projects: passed.
- Ruff on changed and newly added Python files: passed.
- OpenAPI export and generated TypeScript drift checks: passed.
- OpenAPI lint: passed with 27 warnings; no lint errors.
- Documentation structure and links: passed.

The repository runner's remote Docker connection works despite the lack of a
local Docker executable. This supersedes the environment limitation in the
initial inspection below.

Frontend handwritten integration, mock SQL refresh, and full browser journey
verification remain open. The existing inspection results below are historical.

## Inspection baseline and limits

The 2026-10-21 inspection found:

| Check | Result |
| --- | --- |
| Backend Python type check | 38 errors |
| Studio and shared frontend TypeScript check | 155 errors |
| Repository Python tooling type check | Passed |
| CDK Python type check | Passed |
| OpenAPI tooling Python type check | Passed |
| Document validation-path issue | Reproduced directly |
| Real PostgreSQL bootstrap and full backend tests | Not run; Docker and PostgreSQL tools unavailable |
| Browser and complete user-journey verification | Not run |

These counts are a dated baseline, not an estimate of remaining tasks or proof
that every error comes from this migration. Python checks used
`scripts/tools/typecheck.sh`; the `all` run stopped at backend errors, so CDK
and OpenAPI targets were checked separately. The frontend check used installed
TypeScript directly with Studio's configuration after the pnpm launcher refused
to run because its version differed from the repository pin.

## Related documents

- [[responses-and-encryption|Responses and encryption]]
- [[migrations-index|Engineering migrations]]
- [[survey-document-prototype-overview|Survey document prototype overview]]
- [[survey-builder-and-form-filler-migration|Survey builder and form-filler migration manifest]]
