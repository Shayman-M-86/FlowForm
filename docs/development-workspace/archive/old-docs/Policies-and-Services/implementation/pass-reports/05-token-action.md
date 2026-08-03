## Pass report

Changed files:

* `backend/app/services/public_submissions/core/subject_token.py` — added `apply_token_action()` method; dispatches all 5 `TokenAction` values (`issue`, `rotate`, `mark_used`, `keep`, `none`); takes flat scalar inputs (`project_id`, `final_subject_id: UUID`, `token_action`, `existing_raw_token`); returns raw token string or `None`; added `UUID` and `TokenAction` imports
* `backend/app/services/public_submissions/core/session_starter.py` — replaced 20-line inline token dispatch block with single `self._token_service.apply_token_action(...)` call; removed `sub_tok` import; eliminated two redundant `subjects.get_subject` DB calls that were only needed to pass an ORM object into `issue`/`rotate`
* `backend/tests/integration/core/test_token_action.py` — new focused test file

Behavior implemented:

* `apply_token_action` is the single point of entry for all post-resolution token writes
* `issue` → `create_token` for `final_subject_id`; returns raw token
* `rotate` → `get_active_token_for_subject` + `revoke_token` (if found) + `create_token`; returns new raw token
* `mark_used` → `get_active_token_for_subject` + `mark_used` (if found); returns `existing_raw_token` arg so caller can re-set cookie
* `keep` / `none` → no writes; returns `None`
* `session_starter.py` passes `recognition_token` (the browser raw token) as `existing_raw_token` so `mark_used` path can return it

Tests run:

* `bash backend/scripts/run-tests.sh --ai -k "test_token_action"` — 9 passed
* `bash backend/scripts/run-tests.sh --ai -k "test_public_submission_access_grant or test_recognition_token_lookup or test_subject_resolution_result"` — 23 passed (no regression)

Failures or skipped validation:

* none

Trace notes:

* route entry points touched: none
* service methods touched:
  * `SubjectTokenService.apply_token_action` — new method
  * `SessionStarter.start` — token dispatch block replaced with single call
* repository helpers touched: none new; `create_token`, `revoke_token`, `mark_used`, `get_active_token_for_subject` all called from `apply_token_action` only
* side effects changed: token writes consolidated from `session_starter.py` inline block into `SubjectTokenService.apply_token_action`
* transaction boundary changed or unchanged: unchanged — commit still at end of `start()`
* tests that now describe behavior:
  * `test_issue_creates_token_and_returns_raw`
  * `test_issue_returns_new_raw_token_even_when_existing`
  * `test_rotate_revokes_old_token_and_returns_new`
  * `test_rotate_with_no_existing_token_still_issues`
  * `test_mark_used_updates_last_used_at_and_returns_existing_raw`
  * `test_mark_used_no_existing_token_returns_raw_arg`
  * `test_keep_returns_none`
  * `test_none_action_returns_none`
  * `test_keep_does_not_modify_existing_token`

Remaining risks:

* `SubjectTokenService.issue()` and `rotate()` (ORM-arg methods) are now unused — nothing calls them after the dispatch was moved. Target 11 (stale modules) should remove them.
* `apply_token_action` for `mark_used` does a `get_active_token_for_subject` lookup — the token ORM row was already loaded during `SubjectTokenService.lookup()` but is not threaded through. Low risk (extra DB read on the `mark_used` path only). Could be cleaned up in target 06 or 11.

Next recommended pass:

* Target 06: session start orchestration — clean up `session_starter.py` identity write logic and the second `get_active_user_identity` call noted as a risk in pass 04.
