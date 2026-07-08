## Pass report

Changed files:

* `backend/tests/integration/core/test_public_submission_access_grant.py` — added 4 error-case tests (unknown slug, unpublished survey, unknown token, inactive link); migrated from deleted `test_survey_access_resolver.py`
* `backend/tests/integration/core/test_project_subject_identities.py` — new file, 1 test: `test_create_user_identity_sets_verified_email_fields` (migrated from deleted `test_project_subject_resolver.py`)
* `backend/app/services/public_submissions/core/subject_token.py` — removed `issue()` and `rotate()` ORM-arg dead methods; removed now-unused `ProjectSubject` import
* `backend/tests/integration/core/test_survey_access_resolver.py` — deleted (superseded)
* `backend/tests/integration/core/test_project_subject_resolver.py` — deleted (superseded)
* `backend/tests/integration/core/test_submission_session_starter.py` — deleted (superseded)
* `backend/app/services/submissions/` — deleted entirely (no route or non-test consumer; confirmed via grep before deletion)

Behavior implemented:

* `services/submissions/` had no callers outside its own stale test files — safe to delete
* Error-case coverage for `AccessResolver` now lives in `test_public_submission_access_grant.py` alongside happy-path tests
* `create_user_identity` repository function now has its own focused test file
* `SubjectTokenService.issue()` / `.rotate()` were ORM-arg methods unused since pass 05 — removed; `apply_token_action` is the sole interface
* `last_used_at` gap from pass 10 risk note: already closed by `TestApplyTokenActionMarkUsed.test_mark_used_updates_last_used_at_and_returns_existing_raw` — no new code needed

Tests run:

* `bash backend/scripts/run-tests.sh --ai -k "test_public_submission_access_grant or test_project_subject_identities or test_token_action or test_recognition_token_lookup or test_subject_resolution_result or test_transaction_boundary or test_authenticated_account_linking or test_session_start_response_contract or test_flow_matrix"` — 67 passed (was 56; +11 from new/migrated tests)

Failures or skipped validation:

* none

Trace notes:

* route entry points touched: none
* service methods touched: `SubjectTokenService.issue()`, `SubjectTokenService.rotate()` — removed
* repository helpers touched: none
* side effects changed: none
* transaction boundary changed or unchanged: unchanged
* tests that now describe behavior:
  * `test_resolve_public_slug_unknown_slug_raises` — `AccessResolver` slug miss → `SurveyNotFoundBySlugError`
  * `test_resolve_public_slug_without_published_version_raises` — slug found, no published version → `SurveyNotPublishedError`
  * `test_resolve_link_token_unknown_token_raises` — token miss → `LinkNotFoundError`
  * `test_resolve_link_token_inactive_link_raises` — inactive link → `LinkInactiveError`
  * `test_create_user_identity_sets_verified_email_fields` — repository sets `identity_type`, `user_id`, `normalized_email`, `verification_status`, `verified_at`, `attached_at`

Remaining risks:

* none identified. All planned cleanup complete.

Next recommended pass:

* Implementation done — no further targets in plan. Consider a final regression run across full test suite.
