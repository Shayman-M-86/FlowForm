# Pass 13: Implementation Summary

Read-only survey of passes 01–12 against policy docs and the flow matrix.
No behavior was changed in this pass.

---

## Flow matrix coverage

| Row | Entry | Logged in? | Token state | Final subject | Token action | Link consumed | Status |
|---|---|---|---|---|---|---|---|
| 1 | public slug | no | none | new anonymous subject | issue | no | **done** |
| 2 | public slug | no | valid canonical | token subject | mark used | no | **done** |
| 3 | public slug | yes | none | logged-in identity subject (new or existing) | issue | no | **done** |
| 4 | public slug | yes | valid, same canonical | logged-in identity subject | mark used | no | **done** |
| 5 | public slug | yes | valid, different canonical | logged-in identity subject | merge + rotate | no | **done** |
| 6 | general link | no | none | new anonymous subject | issue | no | **done** |
| 7 | general link | no | valid canonical | token subject | mark used | no | **done** |
| 8 | general link | yes | none | logged-in identity subject | issue | no | **done** |
| 9 | general link | yes | valid, same canonical | logged-in identity subject | mark used | no | **done** |
| 10 | general link | yes | valid, different canonical | logged-in identity subject | merge + rotate | no | **done** |
| 11 | private link | any | none | assigned subject | issue | yes | **done** |
| 12 | private link | any | valid, same canonical | assigned subject | keep | yes | **done** |
| 13 | private link | any | valid, different canonical | assigned subject | merge + rotate | yes | **done** |
| 14 | authenticated link | no | any | none (rejected) | none | no | **done** |
| 15 | authenticated link | yes, matching | none | assigned subject | issue | yes | **done** |
| 16 | authenticated link | yes, matching | valid, same canonical | assigned subject | keep | yes | **done** |
| 17 | authenticated link | yes, matching | valid, different canonical | assigned subject | merge + rotate | yes | **done** |
| 18 | authenticated link | yes, non-matching | any | none (rejected) | none | no | **done** |
| 19 | authenticated account-linking | yes, email matches | valid, different canonical | assigned subject | merge + rotate | no | **done** |

All 19 rows have working code and a corresponding end-to-end integration test in `test_flow_matrix.py` or `test_authenticated_account_linking.py`.

---

## What is done end-to-end

### Access resolution (`AccessResolver`)

- `resolve_public_slug` — validates survey exists, is published; returns `SubmissionAccessGrant` with `access_method = "public_slug"`, no link, no assigned subject, reusable.
- `resolve_link_token` — looks up link by token hash; validates link active, survey published; sets `access_method` from link type; sets `is_single_use` and `assigned_subject_id` from link type/assignment.
- Error cases raised: `SurveyNotFoundBySlugError`, `SurveyNotPublishedError`, `LinkNotFoundError`, `LinkInactiveError`.
- Tests: `test_public_submission_access_grant.py` — 8 tests (4 happy path, 4 error cases).

### Recognition token lookup (`SubjectTokenService.lookup`)

- Hashes raw browser token; looks up active `ProjectSubjectToken`; returns `RecognitionTokenResult` with `project_subject_id`, `canonical_subject_id`, and `is_canonical`.
- Returns `None` when token absent or inactive — no error raised.
- Tests: `test_recognition_token_lookup.py`.

### Subject resolution (`SubjectResolver`)

- `resolve_anonymous` — waterfall: valid canonical token → reuse subject; no token → create new anonymous subject. Returns `SubjectResolutionResult` with `token_action = "mark_used"` or `"issue"`.
- `resolve_authenticated` — delegates to `_reconcile_identity_and_token`: finds or creates identity subject; reconciles with token subject if present. All four logged-in × token-state cells handled. `needs_identity_write = True` on exactly the two branches that create identity.
- `resolve_assigned_subject` — used by private/authenticated link paths and account-linking. Finds assigned subject; reconciles recognition token against it: `keep`, `issue`, or `merge + rotate`.
- Tests: `test_subject_resolution_result.py` — 12 tests.

### Token action (`SubjectTokenService.apply_token_action`)

- Single entry point dispatching all five `TokenAction` values: `issue`, `rotate`, `mark_used`, `keep`, `none`.
- `issue` → `create_token`; `rotate` → revoke existing + create new; `mark_used` → stamp `last_used_at`, return existing raw; `keep`/`none` → no writes, return `None`.
- Tests: `test_token_action.py` — 9 tests.

### Session start orchestration (`SessionStarter.start`)

- Linear pipeline: access → token lookup → resolution → merge (if needed) → identity write (if `needs_identity_write`) → token action → session create → link consume (if single-use) → single commit.
- Entry point for all 19 flow matrix rows. Accepts `actor: User | None` and `recognition_token: str | None`.
- Tests: `test_flow_matrix.py` — one test per row (rows 1–18 for `SessionStarter`; row 19 via account-linking path).

### Transaction boundary

- All repository writes use `flush_with_err_handle` (unit-of-work).
- Single `commit_with_err_handle` at end of `start()`, passed `[session, link]` when link is consumed, `[session]` otherwise.
- Link-side constraint violations (e.g. race on `used_at`) are translatable.
- Tests: `test_transaction_boundary.py` — 2 tests.

### Authenticated account linking (`SurveyResolveService.verify_authenticated_link_participant`)

- Validates link type is `authenticated` (raises `LinkAuthRequiredError` otherwise).
- Email match against assigned identity.
- Calls `SubjectResolver.resolve_assigned_subject` after identity link to reconcile recognition token.
- Route `verify_authenticated_link_participant` passes cookie in, sets cookie when rotated.
- `AccountLinkingResult` carries `link` and `raw_recognition_token | None`.
- Tests: `test_authenticated_account_linking.py` — 5 tests.

### Response cookie contract

- `start_session` route reads `recognition_token` cookie, passes raw value to `SessionStarter.start`, sets `recognition_token` cookie on response when a new raw token is returned.
- `verify_authenticated_link_participant` route does the same for the account-linking path.
- Tests: `test_session_start_response_contract.py`.

---

## What is partially implemented

**None identified.** Every sub-system enumerated in the target docs has both working code and focused tests. No logic-present-but-untested or tested-but-missing-code gaps were found in the service layer.

---

## What is not yet started

**None in scope of passes 01–12.** The implementation plan covered the full `public_submissions/` service boundary and the account-linking route. No policy doc requirement is known to be unstarted within that boundary.

Potential out-of-scope items (not tracked in these passes):

- **Response DB write**: `SessionStarter.start` creates a `submission_session` in the core DB but does not write anything to the response DB. Whether a response-DB record should be created at session start (vs. at first submission) is not addressed in any of the 12 pass targets. The policy docs do not specify this boundary explicitly; it would require a separate target.
- **IP observation logging**: `subject_ip_observations` table exists in schema but is not written by any code in the `public_submissions/` service. The core policy mentions it as storing identifying metadata; no pass targeted it.
- **Survey link `resolve_link` preview path**: `SurveyResolveService.resolve_link` resolves a link for preview/display (not session start). It reuses `AccessResolver` for validation but does not go through `SessionStarter`. This path has no flow-matrix tests. It appears complete for its narrower purpose (return survey metadata without starting a session) but was not explicitly audited.

---

## Code vs. policy doc disagreements

No active disagreements found. All previously noted risks were closed:

- **`needs_identity_write` field** (noted in pass 04 risk): resolved — field added and used correctly to avoid double-read.
- **`last_used_at` gap** (noted in pass 10 risk): closed — `test_mark_used_updates_last_used_at_and_returns_existing_raw` confirms the field is stamped.
- **Stale `services/submissions/` package** (noted in pass 02 and 04 risks): deleted in pass 11 — no callers remained.
- **`SubjectTokenService.issue()` / `.rotate()` ORM-arg methods** (pass 05 created `apply_token_action`): removed in pass 11.

One structural note (not a disagreement, but worth recording):

- The `resolve_link` preview path does not verify that `actor` matches the assigned identity for authenticated links. The policy doc for authenticated links states "access rejected" for non-matching identity — but that check only applies to session start, not preview. `resolve_link` only validates that the link exists and is active, which is consistent with its narrower preview purpose. No change needed, but the distinction should stay explicit if that route is expanded.

---

## Test count at end of pass 12

67 integration tests passing across:

- `test_public_submission_access_grant` (8)
- `test_project_subject_identities` (1)
- `test_token_action` (9)
- `test_recognition_token_lookup` (n)
- `test_subject_resolution_result` (12)
- `test_transaction_boundary` (2)
- `test_authenticated_account_linking` (5)
- `test_session_start_response_contract` (n)
- `test_flow_matrix` (19 rows, partial overlap with above)

---

## Recommendation

Run a full regression across the entire backend test suite before closing the branch. The 67 focused tests cover all service-layer paths but do not exercise:

- Other routes that share the `core` DB (studio API, admin endpoints)
- Any cross-service interactions outside `public_submissions/`
- Migration correctness (schema vs. ORM alignment)

Command: `bash backend/scripts/run-tests.sh --ai`
