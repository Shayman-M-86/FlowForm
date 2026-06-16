## Pass report

Changed files:
* `backend/app/schema/api/responses/submission_sessions.py` — added `survey_schema: dict[str, Any] | None = None` field to `PublicSubmissionSessionResponses`
* `backend/app/services/public_submissions/core/session_starter.py` — populate `survey_schema` from `access.published_version.compiled_schema` when `access_method == "public_slug"`; None for all link-based paths
* `backend/tests/integration/core/test_session_start_response_contract.py` — 5 new tests

Behavior implemented:

* Public slug session start now returns `survey_schema` in the response body, matching the policy doc requirement that the respondent-facing survey schema is returned with the session start response (no separate pre-session schema-fetch phase for public slug)
* Link-based session starts (general, private, authenticated) return `survey_schema = None` — schema was already returned at pre-session link resolve time (`POST /links/resolve`)
* Token delivery unchanged and confirmed correct: browser session token and recognition token go exclusively in httponly secure cookies, not in the response body
* Pre-session link resolve (`POST /links/resolve`) already returns `link + survey + published_version` covering the schema requirement for all link-based flows — no change needed there

Tests run:
* `bash backend/scripts/run-tests.sh --ai -k "test_session_start_response_contract"` — 5 passed
* `bash backend/scripts/run-tests.sh --ai -k "test_public_submission_access_grant or test_recognition_token_lookup or test_token_action or test_subject_resolution_result or test_transaction_boundary or test_authenticated_account_linking or test_session_start_response_contract"` — 44 passed

Failures or skipped validation:
* none

Trace notes:
* route entry points touched: none — `POST /submission-session/start` routes through unchanged; response serialisation via `model_dump(mode="json")` picks up the new field automatically
* service methods touched: `SessionStarter.start` — added `survey_schema` conditional at response construction; no new data fetch needed (`access.published_version.compiled_schema` already in scope)
* repository helpers touched: none
* side effects changed: none — schema is read-only from the already-fetched `published_version`
* transaction boundary changed or unchanged: unchanged
* tests that now describe behavior:
  * `test_public_slug_session_start_includes_survey_schema` — confirms schema present for public slug
  * `test_general_link_session_start_omits_survey_schema` — confirms schema absent for general link
  * `test_private_link_session_start_omits_survey_schema` — confirms schema absent for private link
  * `test_public_slug_session_start_returns_browser_session_token` — confirms browser session token returned for cookie
  * `test_public_slug_session_start_returns_recognition_token_for_new_subject` — confirms recognition token issued for new anonymous subject

Remaining risks:
* `last_used_at` update path: docs require `last_used_at` to be updated when the recognition token participates in open-access subject resolution (public slug / general link); `SubjectResolver` currently never returns `token_action = "mark_used"`, so this field is never updated. Target 10 should close this gap.
* `SubjectTokenService.issue()` and `rotate()` (ORM-arg methods) remain unused since pass 05 — target 11 should remove them
* `ProjectSubjectResolver` in `services/submissions/` remains divergent from the new `SubjectResolver` — target 11 should decommission it

Next recommended pass:
* Target 10: `last_used_at` update path — `SubjectResolver` must return `token_action = "mark_used"` when the recognition token participates in open-access subject resolution (public slug / general link) so `apply_token_action` updates the timestamp
