---
paths: backend/app/services/**
---

# backend/app/services/

_Last verified: 2026-06-15_

Service layer = orchestration over domain rules + repositories.

- input -> `Session`, request DTOs/ids, usually `actor`
- load/write -> repositories
- policy -> `app.domain` guard/rule funcs
- commit -> `commit_with_err_handle()` in service, not repo
- output -> ORM rows or result dataclasses from `services/results.py`

Access/RBAC -> `services/access/access_service.py`:

- `AccessService` resolves project/survey membership + permissions
- `require_project_permission()` / `require_survey_permission()` decorate API
  routes, cache access on `flask.g`, attach OpenAPI RBAC metadata
- platform admins bypass membership checks

Respondent-session work -> `services/submissions/`:

- `SurveyAccessResolver` -> public slug/link token access
- `ProjectSubjectResolver` -> assigned link, authenticated user, recognition
  token, optional anonymous subject policy
- `SessionStarter` -> core `submission_sessions` row + browser token hash

No live `SubmissionIntakeService` / `SubmissionGateway`. No response-DB write
or cross-DB orchestration service yet; response-envelope/answer services remain
future work.
