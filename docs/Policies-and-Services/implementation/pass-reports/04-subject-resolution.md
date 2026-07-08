## Pass report

Changed files:

* `backend/app/services/results.py` — added `TokenAction` type alias and `SubjectResolutionResult` dataclass
* `backend/app/services/public_submissions/core/subject_resolver.py` — full rewrite: new `resolve()` signature takes flat scalar inputs; `resolve_assigned_subject`, `resolve_for_open_access`, `_reconcile_identity_and_token` return `SubjectResolutionResult`; added `_resolve_to_canonical` helper; removed all inline token and identity side effects
* `backend/app/services/public_submissions/core/session_starter.py` — updated to call token lookup first, pass scalar fields to resolver, unpack `SubjectResolutionResult`; applies merge writes, identity writes, and token mechanics based on `token_action` before session create
* `backend/tests/integration/core/test_subject_resolution_result.py` — new focused test file

Behavior implemented:

* `SubjectResolutionResult` carries: `final_subject_id`, `subject_source`, `token_action` (`issue|rotate|keep|mark_used|none`), `merge_subject_id`, `merge_into_subject_id`
* `_resolve_to_canonical` follows `canonical_subject_id` one level before comparisons (doc: do not create canonical chains)
* Open-access 7 cases from `logged-in-reconciliation.md` decision table all produce correct `token_action` and `merge_*` fields
* Assigned-access 3 cases from `subject-resolution.md` decision table produce correct `token_action` and `merge_*` fields
* Assigned subject itself resolved to canonical before becoming `final_subject_id`
* All canonical comparisons use resolved canonical IDs, not raw input IDs
* `session_starter.py`: merge write (`set_canonical_subject`) applied before token mechanics; identity write applied only when `subject_source == "authenticated_user"` and no existing identity; token mechanics dispatched on `token_action`

Tests run:

* `bash backend/scripts/run-tests.sh --ai -k "test_subject_resolution_result"` — 12 passed
* `bash backend/scripts/run-tests.sh --ai -k "test_public_submission_access_grant or test_recognition_token_lookup"` — 11 passed (no regression)

Failures or skipped validation:

* none

Trace notes:

* route entry points touched: none
* service methods touched:
  * `SubjectResolver.resolve` — new signature, dispatches on `access_method` string
  * `SubjectResolver.resolve_assigned_subject` — no more SurveyLink ORM arg; takes scalar `assigned_subject_id`
  * `SubjectResolver.resolve_for_open_access` — removed internal `mark_used` call (was temp in pass 03); returns result only
  * `SubjectResolver._reconcile_identity_and_token` — removed internal `rotate`/identity writes; returns result only
  * `SubjectResolver._resolve_to_canonical` — new helper
  * `SessionStarter.start` — token lookup now explicit before resolver call; merge/identity/token mechanics applied from result
* repository helpers touched: none new; `set_canonical_subject`, `get_subject`, `get_active_user_identity`, `create_user_identity`, `get_active_token_for_subject`, `mark_used` called from `session_starter.py` only
* side effects changed: merge writes, identity writes, token mechanics moved from resolver into orchestrator (`session_starter.py`)
* transaction boundary changed or unchanged: unchanged — commit still at end of `start()`
* tests that now describe behavior:
  * `test_open_access_no_token_no_actor_creates_subject_issues_token`
  * `test_open_access_valid_token_no_actor_mark_used`
  * `test_open_access_token_pointing_to_non_canonical_resolves_to_canonical`
  * `test_open_access_logged_in_no_identity_no_token_creates_subject`
  * `test_open_access_logged_in_no_identity_valid_token_attaches`
  * `test_open_access_logged_in_identity_exists_no_token_issues`
  * `test_open_access_logged_in_identity_token_same_canonical_mark_used`
  * `test_open_access_logged_in_identity_token_different_canonical_merges`
  * `test_assigned_no_token_issues_recognition_token`
  * `test_assigned_token_same_canonical_keep`
  * `test_assigned_token_different_canonical_merges_and_rotates`
  * `test_assigned_subject_non_canonical_resolves_to_canonical`

Remaining risks:

* `session_starter.py` calls `subjects.get_subject` a second time for `issue`/`rotate` token action — the subject was already loaded during resolution but not threaded through. Low risk (subject is always present at this point) but an extra DB read. Target 05 or 07 can clean up.
* `_reconcile_identity_and_token` case `(no identity, valid token)` returns `token_action="mark_used"` — but the doc table row "Yes | Valid | No | Token subject | Attach user identity to token subject; update token `last_used_at`" means identity attachment also happens. Orchestrator does write the identity in this case (checks `subject_source == "authenticated_user"` and no existing identity), but the check relies on a second `get_active_user_identity` call in orchestrator — that second call is correct but could be removed when orchestrator carries the identity result from resolution. Target 06 (session start orchestration) may address this.
* Old `ProjectSubjectResolver` in `services/submissions/` is now divergent from the new `SubjectResolver`. Target 11 (stale modules) should decommission the old one.

Next recommended pass:

* Target 05: token action — `SubjectTokenService` should apply the `token_action` instruction from `SubjectResolutionResult` directly, cleaning up the dispatch logic in `session_starter.py` and removing the redundant `get_subject` DB calls.
