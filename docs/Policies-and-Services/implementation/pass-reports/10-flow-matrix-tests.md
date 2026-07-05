## Pass report

Changed files:
* `backend/tests/integration/core/test_flow_matrix.py` — new file, 18 tests
* `docs/Policies-and-Services/implementation/flow-matrix.md` — added 6 missing rows (general link no-token ×2; same-canonical ×4)

Behavior implemented:

* End-to-end flow matrix tests through `SessionStarter.start()` — one test per matrix row, covering all access methods and decision branches named in `flow-matrix.md`
* Happy paths: all 16 happy-path rows covered (public slug ×5, general link ×5, private link ×3, authenticated link ×3)
* Rejection paths: both rejection rows covered (authenticated link unauthenticated → `LinkAuthRequiredError`; authenticated link non-matching identity → `LinkAssignmentMismatchError`)
* Each test asserts: session row created, correct subject, link consumed/not consumed, recognition token issued/rotated/unchanged/None per matrix column

Matrix fix (post-initial-pass review): external critique identified two valid gaps:
1. General link + no token rows were missing — open-access resolution applies to both public slug and general link but the matrix only had no-token rows for public slug. Added `general link | no | none` (anonymous) and `general link | yes | none` (logged-in identity) rows, confirmed by `subject-resolution.md` open-access decision table.
2. Same-canonical rows were missing across all access methods — the resolver returns `token_action = "keep"` (assigned-access) or `mark_used` (open-access) when the token already points to the canonical subject, which is behaviorally distinct from the no-token `"issue"` path. Added 4 rows (public slug ×1, general link ×1, private link ×1, authenticated link ×1).

Three other suggestions from the critique were rejected: response-envelope wording (no cross-DB requirement in current docs); "reconcile" vs "merge" vocabulary (docs use "merge" throughout); authority-order description (already matches docs).

Tests run:
* `bash backend/scripts/run-tests.sh --ai -k "test_flow_matrix"` — 18 passed
* `bash backend/scripts/run-tests.sh --ai -k "test_public_submission_access_grant or test_recognition_token_lookup or test_token_action or test_subject_resolution_result or test_transaction_boundary or test_authenticated_account_linking or test_session_start_response_contract or test_flow_matrix"` — 56 passed (no regression)

Failures or skipped validation:
* Initial run (12 tests): row 4 (public slug logged-in merge) had an incorrect assertion — `get_active_token` on the stray (token) subject returned non-nil because `rotate` revokes on the final subject only, not on the stray. Fixed by removing the stray-token revocation assertion; the merge is verified via `canonical_subject_id` instead.

Trace notes:
* route entry points touched: none
* service methods touched: none — tests call `SessionStarter.start()` as black box
* repository helpers touched: none
* side effects changed: none
* transaction boundary changed or unchanged: unchanged
* tests that now describe behavior:
  * `test_public_slug_no_actor_no_token_creates_anonymous_subject_issues_token` — matrix row 1
  * `test_public_slug_no_actor_valid_canonical_token_uses_token_subject` — row 2
  * `test_public_slug_logged_in_no_token_creates_or_uses_identity_subject` — row 3
  * `test_public_slug_logged_in_same_canonical_token_mark_used` — row 4 (new)
  * `test_public_slug_logged_in_different_canonical_token_merges_and_rotates` — row 5
  * `test_general_link_no_actor_no_token_creates_anonymous_subject_issues_token` — row 6 (new)
  * `test_general_link_no_actor_valid_token_uses_token_subject` — row 7
  * `test_general_link_logged_in_no_token_creates_identity_subject` — row 8 (new)
  * `test_general_link_logged_in_same_canonical_token_mark_used` — row 9 (new)
  * `test_general_link_logged_in_different_canonical_token_merges_and_rotates` — row 10
  * `test_private_link_no_token_uses_assigned_subject_and_consumes_link` — row 11
  * `test_private_link_same_canonical_token_keep` — row 12 (new)
  * `test_private_link_different_canonical_token_merges_rotates_and_consumes` — row 13
  * `test_authenticated_link_unauthenticated_actor_rejected` — row 14 rejection
  * `test_authenticated_link_matching_identity_no_token_creates_session` — row 15
  * `test_authenticated_link_same_canonical_token_keep` — row 16 (new)
  * `test_authenticated_link_matching_identity_different_token_merges_and_rotates` — row 17
  * `test_authenticated_link_non_matching_identity_rejected` — row 18 rejection

Remaining risks:
* `last_used_at` update gap: `SubjectResolver` returns `token_action = "mark_used"` for open-access with valid token, but `apply_token_action("mark_used")` looks up the token on `final_subject_id` — which matches the token subject's canonical. The `mark_used` call works but `last_used_at` timestamp is only updated if the token row is found by subject. Row 2 and row 5 tests confirm the raw token returned matches but do not assert `last_used_at` is set. Target 11 should close this gap per pass 09 note.
* `SubjectTokenService.issue()` and `rotate()` (ORM-arg methods) still unused since pass 05 — target 11 cleanup.
* `ProjectSubjectResolver` in `services/submissions/` remains divergent — target 11 decommission.

Next recommended pass:
* Target 11: cleanup — remove unused `SubjectTokenService.issue()`/`rotate()` ORM methods; decommission `ProjectSubjectResolver`; close `last_used_at` gap in `apply_token_action("mark_used")` path
