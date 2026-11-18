---
title: Survey document reconciliation plan
aliases: ["Survey document reconciliation plan"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-11-18
tags: [backend, frontend]
related_code:
  - "../../../backend/app/services/surveys.py"
  - "../../../backend/app/services/public_submissions/api/session_management.py"
  - "../../../frontend/scripts/generate-types.mjs"
  - "../../../frontend/apps/studio-app/src/pages/SurveyWorkspaceTabPages/useSurveyBuilderController.ts"
  - "../../../frontend/apps/studio-app/src/pages/RespondPage.tsx"
related_docs: ["Engineering migrations"]
---

# Survey document reconciliation plan

## Recommendation

Selectively port the document-model work onto reconsolidation. Do not merge the
entire feature branch or replace current files wholesale. Feature has substantial
backend groundwork but an unfinished frontend that still calls removed node APIs.
Transferring that backend alone would break the working application.

Separate two milestones: first land independent contracts, validators, tests and
portable UI without switching active routes; then activate document surveys only
after the backend, generated contracts and frontend adapters work together in an
isolated integration candidate. That integration is necessary migration work;
subsequent product development can follow separately.

This is an inspected proposal, not completed implementation. Application code,
active routes, databases and deployments were not changed.

## Frontend source boundary

Owner decision on 2026-11-18: **do not migrate anything under `frontend/`
from the feature branch.** Reconsolidation's frontend is the authoritative base;
its recent work has addressed the relevant concerns in its own way.

This exclusion includes handwritten components, table/responsiveness changes,
styles, public-site changes, tests, configuration, and all generated frontend
API/schema artifacts. It has no migration-dependency exception. The commits
listed below are sources for backend/document-model work; their frontend
changes are excluded.

Any frontend changes required by the document model must be implemented against
reconsolidation's current frontend. Regenerate contracts using reconsolidation's
tooling and the integrated backend; do not copy generated outputs from feature.
Portable builder/filler code from the separate Test-suite prototype is a distinct
source and remains subject to the adapter and verification steps below.

## Verified inputs

| Input | Snapshot on 2026-11-18 |
| --- | --- |
| Base | `codex/reconcile-branches` at `d7c4dc07887f12e3e5bfbaf22399b37fa363bb17` |
| Source | `feature` at `e088fbb967fece4c72e7848af2d0f23b05d9f33e` |
| Common ancestor | `02134e6675216d97a3aa62e3999da183de2af169` |
| Divergence | 62 reconsolidation-only commits; 16 feature-only commits |
| Remote | Live `git ls-remote` matched both local tips |
| Initial FlowForm worktree | Clean |
| Prototype | `/home/shayman86/my-repos/Test-suite`, HEAD `ed3016e`, 11 modified tracked files |

The prototype modifications include its model, actions, content catalogue, ID
helpers, canvas, inspector, exports, demo and README. Preserve this existing user
work and record the intended source snapshot before copying components. Using
prototype HEAD alone would omit changes. No prototype files were changed here.

The supplied `Test-suite/FLOWFORM-MIGRATION.md` was verified on 2026-08-03.
More current migration notes exist at these paths **on feature**:

- `docs/development-workspace/migrations/survey-document-migration-checklist.md`
- `docs/development-workspace/migrations/survey-builder-and-form-filler-migration.md`
- `docs/development-workspace/migrations/survey-document-prototype-overview.md`

The checklist records October inspection and a backend implementation update,
but leaves frontend integration and browser verification open. Its 716 passing
backend tests and four passing Python projects are historical source-branch
evidence, not validation of a reconsolidation port.

## Source changes to extract

| Commit | Actual scope | Treatment |
| --- | --- | --- |
| `84cee601` | Canonical document/field contracts, publication checks, errors, focused tests | Starting point for additive work; carefully merge shared enums/errors/limits |
| `5e34e2dc` | Document SQL/ORM/services, field slots/events/encrypted payloads, generated outputs, deletion of node internals | Port backend/schema changes in dependency order; exclude all frontend files, including generated outputs; do not activate alone |
| `e088fbb9` | Despite its documentation title: document routes, field-answer APIs, results/exports, legacy deletion, fixtures/tests, contracts and notes | Extract backend implementation, backend tests and migration notes; exclude all frontend files |

Reuse the canonical content contracts, publication/answer validators, document
persistence, field-based answer-save/crypto path, result traversal and relevant
tests. Preserve the core/response separation, session envelopes, key lifecycle,
field ownership, pinned versions and latest-answer replacement.

Exclude every frontend change from feature, including table and homepage work.
Also exclude unrelated docs/tooling, CDK, proxy, editor and dependency changes
unless a migration dependency is demonstrated outside the frontend boundary. These three commits are
source material, not a safe blind cherry-pick sequence.

## Reconciliation map

| Area | Observed incompatibility | Required treatment |
| --- | --- | --- |
| AI import | Feature deletes `builder_nodes.py` and `services/content.py`, which now host reconsolidation's AI import | Move generation to document-oriented routes/services before removal. Preserve authentication, edit permission, draft checks, per-user rate limiting, server-side calls, config and errors |
| AI contracts | Prompt, generated import schema, Zod parser and modal describe nodes | Generate document preview validation from canonical contracts; preserve current preview/modal and tracing behaviour |
| Results | Reconsolidation added wording, readable values and order; feature's field map returns only fields | Carry prompt, section, option labels and document order from the frozen definition into backend results and frontend scalar/list formatting |
| Resume | `fe81299d` matches the requested survey/link before status validation; feature checks status first | Preserve current ordering and `test_submission_session_resume.py` regressions for stale/completed cookies belonging to other entries |
| Studio | Current controller saves node diffs and recovers node-shaped drafts | Use document operations behind the host controller; retain dirty switching, permissions, copy/archive/publish, published read-only view, publish/share modal and errors |
| New drafts | Current controller assumes zero nodes; feature requires a definition with sections and blocks | Define valid initial content or deliberately revise draft validation; remove empty-node cache assumptions |
| Respondent | Current page reads `compiled_schema.nodes`, maps family envelopes and calls UUID node paths | Use `definition.document.sections`, string field IDs and `{client_mutation_id,state,value}` while retaining resolve/start/resume/save/complete orchestration |
| Codegen | Feature builder-generated files are header-only while handwritten consumers still import node types | Add supported document type/runtime-validator generation. Use reconsolidation tooling; retain its legacy outputs while active node code needs them and regenerate from integrated sources. Import no feature frontend artifacts |
| Public site | Marketing demos consume current builder/filler exports | Preserve or migrate these consumers before deleting shared exports; keep reconsolidation homepage |
| Platform | Reconsolidation owns newer auth routing, Tailwind ordering, tracing, hybrid/Cloudflare, secrets, dependencies and security fixes | Keep integration-base versions; avoid incidental rollback |

A successful textual merge would not resolve these dependencies.

## Contract gaps to settle during integration

- Prototype options have `key` and optional `description`; feature accepts only
  `id` and `label`. Define a lossless round trip.
- Prototype uses text `phone`, rating `faces`, choice `pills` and numeric prefix;
  feature uses `tel`, `emoji`, omits pills and has no prefix. Map synonyms and
  retain supported presentation choices instead of degrading the UI.
- Keep title/status/revision in the host. Content JSON uses camelCase aliases;
  do not apply blanket snake_case conversion to documents.
- Strict saved-content validation conflicts with intermediate empty authoring
  states. Define local-draft versus explicit-save behaviour and precise errors.
- Revision increments are not optimistic locking: replacement requests have no
  expected revision and repository writes are unconditional. Settle concurrent
  save behaviour before claiming overwrite protection.
- Resume returns pinned survey context, not a saved-answer collection. Define
  an authorized restoration path if server-backed answer restoration is needed.
- The portable filler callback is synchronous with a saved timestamp. Production
  adapters need pending/error/retry state and must await acknowledged saves
  before completion.
- Older decisions specify latest-answer-only storage, retained hidden answers,
  frontend visibility/required-answer logic and no new backend completion engine.
  Preserve intended scope rather than silently adding features.
- Feature records an October fresh-data reset decision. This is historical
  context, not authorization to reset today's databases. Establish target
  environments and data policy before deployment.

## Execution sequence

1. Capture current checks and create/publish/respond/results journeys. When
   implementation starts, use a separate integration branch/worktree based on
   reconsolidation and preserve prototype user changes.
2. Import independent contracts, validators and focused tests. Merge shared
   definitions surgically; retain active node storage/routes/exports/codegen.
   Existing and new checks must pass.
3. Snapshot the intended prototype source and import portable components into a
   separate namespace. Exclude demo shell/theme/persistence. Add narrow adapters
   and a development-only harness; both apps and old journeys must still work.
4. In the isolated candidate, coordinate document SQL/ORM/services, field APIs/
   slots/crypto, results, mock fixtures, Studio, respondent flow and AI import.
   Implement frontend adaptations on reconsolidation and regenerate contracts
   with its tooling; import no frontend files from feature. Do not deploy
   incompatible intermediate commits alone.
5. Verify isolated fresh core/response databases and the full browser journey
   before switching the working application's active behaviour.
6. Agree data/reset policy and deploy matching backend/frontend/schema versions.
   Retain a recoverable database snapshot and code release: code rollback alone
   cannot undo destructive schema replacement.
7. Retire node/scoring APIs, generated exports, draft/preview storage and obsolete
   tests only after every consumer is verified. Update maintained documentation
   from implementation evidence and archive superseded migration records.

Steps 2-3 can land without activating document surveys. Steps 4-5 are necessary
integration, not later product expansion. Two active production storage models
would be a larger, separately justified compatibility project.

## Acceptance gates

- Inspect the backend runner, then use `bash backend/scripts/run-tests.sh --ai`
  on isolated fresh PostgreSQL databases. Include document tests plus current
  AI/results/resume regressions and appropriate Python checks.
- OpenAPI export/lint and all generation/drift checks, including document types,
  runtime validators and AI import contracts. Never hand-merge generated outputs.
- Studio build/typecheck/lint/tests and public-site checks/build. Preserve current
  published-read-only, publish-success, AI modal, results formatting/polling,
  naming, auth/routing, tracing and shared-style regression coverage.
- Full journey: create -> edit/recover draft -> save -> switch/copy -> publish ->
  share -> answer -> refresh/resume -> complete -> readable ordered results ->
  CSV/JSON export.
- Both themes and desktop/mobile; focus, conditional visibility, retained hidden
  answers, mobile sequencing, preview-only phone frame, failed saves/retries and
  completion with pending saves.
- Permissions, publication immutability, pinned versions, field ownership,
  repeated saves/clearing/fresh nonces and cross-database failure handling.
  Response storage must still exclude plaintext core identifiers/answer values.
- Actual target bootstrap and compatible mock fixtures. Feature replaces
  baseline SQL rather than supplying an upgrade migration. Mock SQL still
  inserts `compiled_schema`, question/scoring rows and node events; current AWS
  bootstrap tests expect the old core table count. Refresh these inputs without
  importing unrelated infrastructure changes.

## Evidence and limits

Executed branch/status/history inspection, live remote tip comparison,
commit-level diffs, focused code/document/prototype inspection and
`git merge-tree --write-tree --name-only HEAD feature`. The full-branch rehearsal
reported 42 conflicted paths across application, generated files, documentation,
tooling, editor and CDK files. It wrote merge-result Git objects without applying
a merge or changing HEAD, index or working files.

No application suite, browser journey, database bootstrap or deployment was run.
Current baseline health and candidate runtime compatibility remain unverified.
The intended working-tree changes are this proposal and its migration-index
entry. No commits or pushes were made.
