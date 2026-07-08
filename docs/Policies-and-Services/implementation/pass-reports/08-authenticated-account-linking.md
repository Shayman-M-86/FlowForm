## Pass report

Changed files:

* `backend/app/services/results.py` — added `AccountLinkingResult` dataclass
* `backend/app/services/public_submissions/api/survey_resolve.py` — fixed link_type guard; added recognition token reconciliation after identity linking; updated return type from `SurveyLink` to `AccountLinkingResult`; added `SubjectResolver` and `SubjectTokenService` collaborators
* `backend/app/api/v1/public.py` — updated `verify_authenticated_link_participant` route to pass recognition cookie in, and set recognition cookie when token was rotated
* `backend/tests/integration/core/test_authenticated_account_linking.py` — 5 new tests

Behavior implemented:

* Non-authenticated links sent to the account-linking endpoint now raise `LinkAuthRequiredError` (was silently returning the link)
* After email match and identity linking, the browser recognition token is reconciled against the assigned subject using `SubjectResolver.resolve_assigned_subject`
* If the token points to a different subject, the token subject's `canonical_subject_id` is set to the assigned subject (merge), and the token is rotated — browser receives a new recognition cookie
* If the token already points to the assigned subject (direct match), `token_action = "keep"` and no cookie is returned
* If no browser token is present, a new token is issued for the assigned subject and returned as a cookie
* `AccountLinkingResult` carries `link` and `raw_recognition_token | None` so the route handler can conditionally set the cookie

Tests run:

* `bash backend/scripts/run-tests.sh --ai -k "test_authenticated_account_linking"` — 5 passed
* `bash backend/scripts/run-tests.sh --ai -k "test_public_submission_access_grant or test_recognition_token_lookup or test_token_action or test_subject_resolution_result or test_transaction_boundary or test_authenticated_account_linking"` — 39 passed

Failures or skipped validation:

* none

Trace notes:

* route entry points touched: `POST /links/verification/link` (`verify_authenticated_link_participant` in `api/v1/public.py`)
* service methods touched: `SurveyResolveService.verify_authenticated_link_participant` — full rewrite of return type and post-linking behavior
* repository helpers touched: `project_subjects.get_subject`, `project_subjects.set_canonical_subject` (merge path only); `project_subject_tokens.create_token`, `get_active_token_for_subject`, `revoke_token` (via `apply_token_action`)
* side effects changed: account-linking endpoint now writes `canonical_subject_id` on token subject rows when merge is needed, and creates/rotates recognition tokens; previously it only wrote the `user_id` link on the identity row
* transaction boundary changed or unchanged: the merge flush, token revoke/create, and identity link each use `flush_with_err_handle` inside their respective repository helpers; `verify_participant_for_user` calls `commit_with_err_handle` after linking the identity — all writes commit in that single call (merge and token writes flush before the commit)
* tests that now describe behavior:
  * `test_non_authenticated_link_raises_on_account_linking_endpoint` — confirms link_type guard
  * `test_email_mismatch_raises` — confirms email check still enforced
  * `test_email_match_no_browser_token_issues_token` — confirms new token issued when no browser token
  * `test_browser_token_same_subject_no_cookie_rotation` — confirms keep path returns None
  * `test_browser_token_different_subject_rotated` — confirms merge + rotate path, asserts `canonical_subject_id` on weaker subject

Remaining risks:

* `SubjectTokenService.issue()` and `rotate()` (ORM-arg methods) remain unused since pass 05 — target 11 should remove them
* `ProjectSubjectResolver` in `services/submissions/` remains divergent from the new `SubjectResolver` — target 11 should decommission it
* The merge and token writes are flushed before the commit in `verify_participant_for_user`, but they are not part of `commit_with_err_handle`'s context list — a constraint error on the token or merge row would surface as an unhandled DB error rather than a translated domain error

Next recommended pass:

* Target 09: verify `last_used_at` update path — docs require `last_used_at` to be updated when the recognition token participates in open-access subject resolution (public slug / general link), but not for assigned links
