# Target 01: Runtime Inventory

## Context pack: target 01 runtime inventory

Relevant docs:

* `docs/Policies-and-Services/core-policies.md`
* `docs/Policies-and-Services/Flows/Public-slug-flow.md`
* `docs/Policies-and-Services/Flows/General-Link-Flow.md`
* `docs/Policies-and-Services/Flows/Private-link-access-Flow.md`
* `docs/Policies-and-Services/Flows/Authenticated-link-access-Flow.md`

Current code:

* `backend/app/api/v1/public.py`
* `backend/app/services/public_submissions/api/session_management.py`
* `backend/app/services/public_submissions/api/survey_resolve.py`
* `backend/app/services/public_submissions/core/access_resolver.py`
* `backend/app/services/public_submissions/core/subject_resolver.py`
* `backend/app/services/public_submissions/core/subject_token.py`
* `backend/app/services/public_submissions/core/session_starter.py`
* `backend/app/services/results.py`

Direct callers:

* `backend/app/api/v1/public.py`

Direct tests:

* `backend/tests/e2e/test_submission_session_start.py`
* `backend/tests/unit/test_submission_session_contracts.py`
* `backend/tests/integration/core/test_submission_session_starter.py`
* `backend/tests/integration/core/test_project_subject_resolver.py`
* `backend/tests/integration/core/test_survey_access_resolver.py`

Known mismatch:

* `SubmissionAccessGrant` is ORM-heavy: `survey`, `published_version`, `link`.
* Policy wants explicit grant fields: `access_method`, ids, assigned subject candidate, auth requirement, and single-use flag.
* Flow docs say session start returns schema and tokens; current route and tests lock minimal JSON body plus cookies.

Expected output contract:

* Inventory only. No behavior edit.

Risk level:

* Medium. Next pass touches service contract.

## Current route -> service -> repository flow map

* `GET /api/v1/public/surveys`
  * `SurveyResolveService.list_public_surveys`
  * `surveys_repo.list_public_surveys`

* `GET /api/v1/public/surveys/<public_slug>`
  * `SurveyResolveService.get_public_survey`
  * `surveys_repo.get_by_public_slug`
  * `surveys_repo.get_published_version`

* `POST /api/v1/public/links/resolve`
  * `SurveyResolveService.resolve_link`
  * `public_link_repo.resolve_token`
  * `AccessResolver.resolve_link_token`
  * `surveys_repo.get_survey`
  * `submission_access_rules.ensure_link_token_access`
  * `surveys_repo.get_published_version`

* `POST /api/v1/public/links/verification/link`
  * `SurveyResolveService.verify_authenticated_link_participant`
  * `public_link_repo.resolve_token`
  * `public_link_rules` checks
  * `project_participants.get_participant`
  * `ParticipantService.verify_participant_for_user`

* `POST /api/v1/public/submission-session/start`
  * `SessionManagementService.start_session`
  * `SessionStarter.start`
  * `AccessResolver.resolve`
  * public slug path:
    * `surveys_repo.get_by_public_slug`
    * `surveys_repo.get_published_version`
  * link token path:
    * `public_link_repo.resolve_token`
    * `surveys_repo.get_survey`
    * `submission_access_rules.ensure_link_token_access`
    * `surveys_repo.get_published_version`
  * `survey_rules.ensure_has_response_store`
  * `SubjectResolver.resolve`
  * `SubjectTokenService.lookup`, `SubjectTokenService.issue`, or `SubjectTokenService.rotate`
  * `project_subject_tokens`, `project_subjects`, `project_subject_identities`
  * `submission_sessions.generate_browser_session_token`
  * `submission_sessions.create_session`
  * optional `public_link_repo.mark_used`
  * `commit_with_err_handle`

* `PUT /api/v1/public/submission-session/answer`
  * placeholder response wrapper only

* `POST /api/v1/public/submission-session/event`
  * placeholder response wrapper only

* `POST /api/v1/public/submission-session/complete`
  * placeholder response wrapper only

## Hidden consumers or stale old-service consumers

Old service package still exists:

* `backend/app/services/submissions/access_resolver.py`
* `backend/app/services/submissions/project_subject_resolver.py`
* `backend/app/services/submissions/session_starter.py`

No app route imports old package.

Integration tests still import old services:

* `backend/tests/integration/core/test_submission_session_starter.py`
* `backend/tests/integration/core/test_project_subject_resolver.py`
* `backend/tests/integration/core/test_survey_access_resolver.py`

Stale-risk details:

* old `ProjectSubjectResolver` still calls `project_subject_tokens.mark_used`
* new `SubjectTokenService.lookup` also calls `project_subject_tokens.mark_used`
* old services duplicate access/session/subject flow with older semantics
* old tests may preserve stale behavior after `public_submissions` contracts change

## First contract that should change

Change `SubmissionAccessGrant` first.

Current shape:

* `survey`
* `published_version`
* `link | None`

Policy-needed shape:

* `access_method`
* `project_id`
* `survey_id`
* `survey_version_id`
* `link_id | None`
* `assigned_subject_id | None`
* `requires_auth`
* `is_single_use`

Reason:

* `AccessResolver` is first shared boundary used by link resolve and session start.
* Current downstream code infers policy from ORM shape.
* Policy says access validation must return explicit access facts and must not decide final subject.
* Subject/session/token passes need this explicit grant before deeper behavior changes.

Route-response mismatch remains:

* flow docs say session start returns session token, recognition token, schema, and metadata
* current code returns minimal body and sets tokens in cookies
* current tests intentionally assert no survey/schema/answers in response body

Do not change start response before resolving that contract intentionally.

## Pass report

Changed files:

* `docs/Policies-and-Services/implementation/pass-reports/01-runtime-inventory.md`

Behavior implemented:

* none. Runtime inventory only.

Tests run:

* none. No code edit.

Failures or skipped validation:

* validation skipped because target 01 asks inventory, not behavior change.

Trace notes:

* route entry points touched:
  * read-only: `backend/app/api/v1/public.py`
* service methods touched:
  * read-only: `SurveyResolveService.*`
  * read-only: `SessionManagementService.start_session`
  * read-only: `SessionStarter.start`
  * read-only: `AccessResolver.*`
  * read-only: `SubjectResolver.*`
  * read-only: `SubjectTokenService.*`
* repository helpers touched:
  * read-only: `public_link_repo`
  * read-only: `surveys_repo`
  * read-only: `submission_sessions`
  * read-only: `project_subjects`
  * read-only: `project_subject_identities`
  * read-only: `project_subject_tokens`
  * read-only: `project_participants`
* side effects changed:
  * none
* transaction boundary changed or unchanged:
  * unchanged. Current boundary is `SessionStarter.start`, with subject/token/session/link effects committed by `commit_with_err_handle`.
* tests that now describe behavior:
  * existing e2e/unit tests lock minimal session-start response and cookies.

Remaining risks:

* old `app.services.submissions` tests still pin stale service behavior
* `SubmissionAccessGrant` is too implicit for policy flow matrix
* assigned-link token cleanup is not fully represented in current `SubjectResolver.resolve_assigned_subject`
* docs and current session-start response body disagree on schema/tokens

Next recommended pass:

* target 02: access grant contract
