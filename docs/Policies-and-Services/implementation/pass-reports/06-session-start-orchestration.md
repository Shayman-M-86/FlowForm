## Pass report

Changed files:

* `backend/app/services/results.py` — added `needs_identity_write: bool = False` field to `SubjectResolutionResult`
* `backend/app/services/public_submissions/core/subject_resolver.py` — set `needs_identity_write=True` on the two `identity is None` branches in `_reconcile_identity_and_token`: (a) no identity + valid token → attach identity; (b) no identity + no token → new subject + create identity
* `backend/app/services/public_submissions/core/session_starter.py` — replaced identity-write guard block (which called `get_active_user_identity` a second time to check for an existing identity) with a single `if actor is not None and resolution.needs_identity_write` check; removed the redundant `sub_id.get_active_user_identity` call
* `backend/tests/integration/core/test_subject_resolution_result.py` — added `needs_identity_write is True` assertions to `test_open_access_logged_in_no_identity_no_token_creates_subject` and `test_open_access_logged_in_no_identity_valid_token_attaches`; added `needs_identity_write is False` assertions to the three identity-exists cases

Behavior implemented:

* `SubjectResolutionResult.needs_identity_write` encodes the resolver's knowledge that no user identity row exists yet — eliminating a second `get_active_user_identity` DB read in the orchestrator
* `needs_identity_write=True` on exactly the two doc-table rows where identity must be created: "Yes | None | No" (new subject) and "Yes | Valid | No" (attach to token subject)
* `needs_identity_write=False` (default) on all other branches — identity exists or actor is anonymous
* `session_starter.py` step order unchanged: access → token lookup → resolution → merge → identity → token → session → link → commit

Tests run:

* `bash backend/scripts/run-tests.sh --ai -k "test_subject_resolution_result"` — 12 passed
* `bash backend/scripts/run-tests.sh --ai -k "test_public_submission_access_grant or test_recognition_token_lookup or test_token_action"` — 20 passed (no regression)

Failures or skipped validation:

* none

Trace notes:

* route entry points touched: none
* service methods touched:
  * `SubjectResolver._reconcile_identity_and_token` — `needs_identity_write=True` added to two return sites
  * `SessionStarter.start` — identity write guard simplified; `sub_id.get_active_user_identity` call removed
* repository helpers touched: none; `get_active_user_identity` call removed from orchestrator (was redundant — resolver already holds that knowledge)
* side effects changed: one `get_active_user_identity` DB read eliminated on the identity-write path
* transaction boundary changed or unchanged: unchanged — commit still at end of `start()`
* tests that now describe behavior:
  * `test_open_access_logged_in_no_identity_no_token_creates_subject` — asserts `needs_identity_write is True`
  * `test_open_access_logged_in_no_identity_valid_token_attaches` — asserts `needs_identity_write is True`
  * `test_open_access_logged_in_identity_exists_no_token_issues` — asserts `needs_identity_write is False`
  * `test_open_access_logged_in_identity_token_same_canonical_mark_used` — asserts `needs_identity_write is False`
  * `test_open_access_logged_in_identity_token_different_canonical_merges` — asserts `needs_identity_write is False`

Remaining risks:

* Merge block in `session_starter.py` still calls `subjects.get_subject` twice (for `merge_subject_id` and `merge_into_subject_id`) — these are needed because `set_canonical_subject` takes ORM args. Low risk, no doc-driven reason to change now. Target 11 (stale modules) can evaluate.
* `SubjectTokenService.issue()` and `rotate()` (ORM-arg methods) remain unused since pass 05 moved dispatch into `apply_token_action`. Target 11 should remove them.
* `ProjectSubjectResolver` in `services/submissions/` is divergent from the new `SubjectResolver`. Target 11 should decommission it.

Next recommended pass:

* Target 07: transaction boundary — verify all commit-together requirements from the flow matrix are met in `session_starter.py` and confirm link consumption is correctly gated.
