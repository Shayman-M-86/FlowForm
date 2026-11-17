# Target 02: AccessGrant Contract

## Context pack: target 02 access grant

Relevant docs:

* `docs/Policies-and-Services/core-policies.md` — access validation vs subject resolution
* `docs/Policies-and-Services/Flows/shared/resolve-link-token.md` — link context output
* `docs/Policies-and-Services/Flows/Public-slug-flow.md` — public slug grant
* `docs/Policies-and-Services/Flows/General-Link-Flow.md` — general link grant
* `docs/Policies-and-Services/Flows/Private-link-access-Flow.md` — private assigned link grant
* `docs/Policies-and-Services/Flows/Authenticated-link-access-Flow.md` — authenticated assigned link grant

Current code:

* `backend/app/services/results.py`
* `backend/app/services/public_submissions/core/access_resolver.py`
* `backend/app/services/public_submissions/core/session_starter.py`
* `backend/app/services/submissions/access_resolver.py`

Direct callers:

* `backend/app/services/public_submissions/core/session_starter.py`
* `backend/app/services/public_submissions/api/survey_resolve.py`
* stale compatibility caller: `backend/app/services/submissions/access_resolver.py`

Direct tests:

* `backend/tests/integration/core/test_public_submission_access_grant.py`
* existing stale coverage: `backend/tests/integration/core/test_survey_access_resolver.py`
* existing session coverage: `backend/tests/integration/core/test_submission_session_starter.py`

Gap and target contract:

* `SubmissionAccessGrant` carried only ORM handles; downstream inferred policy facts from shape → grant must carry explicit `access_method`, `project_id`, `survey_id`, `survey_version_id`, `link_id`, `assigned_subject_id`, `requires_auth`, `is_single_use`.

Risk level:

* Medium. Service contract changed. Auth behavior unchanged.

## Pass report

Changed files:

* `backend/app/services/results.py`
* `backend/app/services/public_submissions/core/access_resolver.py`
* `backend/app/services/public_submissions/core/session_starter.py`
* `backend/app/services/submissions/access_resolver.py`
* `backend/tests/integration/core/test_public_submission_access_grant.py`
* `docs/Policies-and-Services/implementation/pass-reports/02-access-grant.md`

Behavior implemented:

* `SubmissionAccessGrant` now carries explicit policy context.
* Public slug grant sets `access_method = public_slug`, no link, no assigned subject, no auth, reusable.
* General link grant sets `access_method = general_link`, link id, no assigned subject, no auth, reusable.
* Private link grant sets `access_method = private_link`, link id, assigned subject candidate, no auth, single-use.
* Authenticated link grant sets `access_method = authenticated_assigned_link`, link id, assigned subject candidate, auth required, single-use.
* Session starter now uses grant ids and `is_single_use` instead of re-reading those facts from ORM shape.

Tests run:

* `uv run python -m py_compile` on all touched files — clean
* `uv run ruff check` on all touched files — clean
* `bash backend/scripts/run-tests.sh --ai -k "test_public_submission_access_grant or test_submission_session_starter or test_survey_access_resolver"` — 12 passed

Failures or skipped validation:

* none

Trace notes:

* route entry points touched:
  * none.
* service methods touched:
  * `AccessResolver.resolve_public_slug`
  * `AccessResolver.resolve_link_token`
  * `SessionStarter.start`
  * stale compatibility: `SurveyAccessResolver._resolve_public_slug`
  * stale compatibility: `SurveyAccessResolver._resolve_link`
* repository helpers touched:
  * none.
* side effects changed:
  * none intended.
* transaction boundary changed or unchanged:
  * unchanged. `SessionStarter.start` still commits after session create and optional link consume.
* tests that now describe behavior:
  * `test_public_slug_grant_carries_explicit_access_context`
  * `test_general_link_grant_carries_reusable_link_context`
  * `test_private_link_grant_carries_assigned_subject_candidate`
  * `test_authenticated_link_grant_carries_auth_requirement`

Remaining risks:

* Subject resolver still receives `link` object. Good for this pass; next pass should decide its own contract.
* Stale old `app.services.submissions` path still exists and duplicates access logic.

Next recommended pass:

* target 03: recognition token lookup.
