## Pass report

Changed files:

* `backend/app/services/results.py` — added `RecognitionTokenLookupResult` dataclass
* `backend/app/services/public_submissions/core/subject_token.py` — `lookup()` now returns `RecognitionTokenLookupResult`; removed `mark_used()` call from lookup
* `backend/app/services/public_submissions/core/subject_resolver.py` — added `sub_tok` import; updated open-access path to unpack lookup result, load subject row by id, call `mark_used()` here (temporary; target 05 owns token action)
* `backend/tests/integration/core/test_recognition_token_lookup.py` — new focused test file

Behavior implemented:

* `SubjectTokenService.lookup()` returns structured result: `token_present`, `token_valid`, `token_id`, `token_subject_id`, `canonical_token_subject_id`, `invalid_reason`
* Lookup does not call `mark_used()` — only reports candidate metadata
* `canonical_token_subject_id` populated from `token.subject.canonical_subject_id`; None when subject is canonical
* `SubjectResolver.resolve_for_open_access` unpacks lookup result; loads `ProjectSubject` row by `token_subject_id`; calls `mark_used()` via `get_active_token_for_subject` when token subject found

Tests run:

* `uv run python -m py_compile` on all touched files — clean
* `uv run ruff check` on all touched files — clean
* `bash backend/scripts/run-tests.sh --ai -k "test_recognition_token_lookup"` — 7 passed

Failures or skipped validation:

* none

Trace notes:

* route entry points touched: none
* service methods touched:
  * `SubjectTokenService.lookup` — return type changed
  * `SubjectResolver.resolve_for_open_access` — unpack lookup result, load subject row
* repository helpers touched: none (no new helpers; `get_active_token_for_subject` already existed)
* side effects changed: `mark_used()` now called from resolver, not from lookup — timing unchanged for valid tokens; absent for invalid tokens (correct per doc)
* transaction boundary changed or unchanged: unchanged
* tests that now describe behavior:
  * `test_absent_token_returns_not_present`
  * `test_valid_token_returns_metadata`
  * `test_valid_token_does_not_update_last_used_at`
  * `test_tampered_token_returns_invalid`
  * `test_revoked_token_returns_invalid`
  * `test_token_wrong_project_returns_invalid`
  * `test_token_subject_with_canonical_returns_canonical_id`

Remaining risks:

* `SubjectResolver.resolve_for_open_access` calls `mark_used()` via a second `get_active_token_for_subject` lookup — two DB reads for same token. Target 05 should decide final token-action contract and clean this up.
* `SubjectResolver` still does not resolve candidate subjects to canonical before comparing (e.g. token_subject vs identity_subject comparison uses raw `.id`). That gap belongs to target 04 subject-resolution.
* Resolver `reconcile_identity_and_token` still receives `ProjectSubject | None` — signature unchanged this pass; target 04 will update it to use lookup result fields.

Next recommended pass:

* target 04: subject-resolution — resolver must resolve candidates to canonical before comparing; canonical subject helper behavior to be designed then.
