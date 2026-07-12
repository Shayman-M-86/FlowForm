## Pass report

Changed files:

* `backend/app/services/public_submissions/api/session_management.py` — removed stale `Docs:` ref from `start_session` docstring
* `backend/app/services/public_submissions/api/survey_resolve.py` — removed stale `service-structure.md` ref from module docstring; rewrote `resolve_link` and `verify_authenticated_link_participant` docstrings to explain behavior instead of pointing at flow docs
* `backend/app/services/public_submissions/core/session_starter.py` — rewrote module docstring and class docstring to describe entry point scope and transaction; removed `Docs:` ref from class docstring
* `backend/app/services/public_submissions/core/subject_resolver.py` — rewrote module docstring, class docstring, and all method docstrings to explain waterfall logic, merge conditions, and write responsibility; removed all `Docs:` refs
* `backend/app/services/public_submissions/core/subject_token.py` — rewrote module docstring, class docstring, `lookup`, and `apply_token_action` docstrings; removed all `Docs:` refs
* `.claude/rules/repomap/backend-app-services.md` — replaced deleted `services/submissions/` entries with accurate `services/public_submissions/` module map

Behavior implemented:

* No behavior changes — docstring-only pass
* All `Docs: <file>` redirects replaced with descriptions of what each class/method actually does
* Stale reference to removed `service-structure.md` eliminated from two module docstrings
* Repomap rule file updated to reflect the deleted `services/submissions/` package and the correct `public_submissions/` structure

Tests run:

* `bash backend/scripts/run-tests.sh --ai -k "test_public_submission_access_grant or test_project_subject_identities or test_token_action or test_recognition_token_lookup or test_subject_resolution_result or test_transaction_boundary or test_authenticated_account_linking or test_session_start_response_contract or test_flow_matrix"` — 67 passed

Failures or skipped validation:

* none

Trace notes:

* route entry points touched: none
* service methods touched: none (comments only)
* repository helpers touched: none
* side effects changed: none
* transaction boundary changed or unchanged: unchanged
* tests that now describe behavior: n/a

Remaining risks:

* none

Next recommended pass:

* Implementation complete through pass 12. Consider a full regression run across the entire test suite before closing the branch.
