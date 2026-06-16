## Pass report

Changed files:
* `backend/app/services/public_submissions/core/session_starter.py` — pass both `session` and `access.link` (when present) as contexts to `commit_with_err_handle`, so constraint errors from the link row are translatable
* `backend/tests/integration/core/test_transaction_boundary.py` — two new tests confirming link consumption commits atomically with session creation

Behavior implemented:

* `commit_with_err_handle` now receives `[session, link]` when a single-use link is consumed (`access.is_single_use and access.link is not None`), and `[session]` for all other paths — matching the set of rows that were flushed in that transaction
* Transaction structure was already correct: all repository writes (merge, identity, token, session, link) use `flush_with_err_handle` (unit-of-work only); a single `commit_with_err_handle` at the end of `start()` issues the one commit — this is unchanged
* Error translation now covers link-side constraint violations (e.g. duplicate `used_at` on a race) in addition to session-side violations

Tests run:
* `bash backend/scripts/run-tests.sh --ai -k "test_transaction_boundary"` — 2 passed
* `bash backend/scripts/run-tests.sh --ai -k "test_public_submission_access_grant or test_recognition_token_lookup or test_token_action or test_subject_resolution_result or test_transaction_boundary"` — 34 passed

Failures or skipped validation:
* none

Trace notes:
* route entry points touched: none
* service methods touched: `SessionStarter.start` — `commit_with_err_handle` call updated to include `access.link` in contexts when present
* repository helpers touched: none
* side effects changed: none — one fewer potential `UnhandledDbIntegrityError` on link-side constraint failures at commit
* transaction boundary changed or unchanged: unchanged — single commit at end of `start()`, all flushes before it
* tests that now describe behavior:
  * `test_single_use_link_consumed_atomically_with_session` — asserts session row exists and `link.used_at` is set after a successful start
  * `test_second_start_on_consumed_link_raises_already_used` — asserts `LinkAlreadyUsedError` on a second start attempt, proving `used_at` was persisted by the first commit

Remaining risks:
* Merge block in `session_starter.py` still calls `subjects.get_subject` twice (for `merge_subject_id` and `merge_into_subject_id`) — low risk, no doc-driven reason to change now
* `SubjectTokenService.issue()` and `rotate()` (ORM-arg methods) remain unused since pass 05 moved dispatch into `apply_token_action` — target 11 should remove them
* `ProjectSubjectResolver` in `services/submissions/` is divergent from the new `SubjectResolver` — target 11 should decommission it

Next recommended pass:
* Target 08: verify `last_used_at` update path — docs require `last_used_at` to be updated when the recognition token participates in open-access subject resolution (public slug / general link), but not for assigned links
