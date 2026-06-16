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

Respondent-session work -> `services/public_submissions/`:

- `api/session_management.py` (`SessionManagementService`) -> start/answer/event/complete lifecycle; start delegates to `core/session_starter.py`
- `api/survey_resolve.py` (`SurveyResolveService`) -> slug browsing, link token resolution, authenticated account linking
- `core/access_resolver.py` (`AccessResolver`) -> resolves survey + link grant from slug or token; enforces access rules
- `core/subject_resolver.py` (`SubjectResolver`) -> priority waterfall: identity > token > new anonymous; returns merge/token instructions
- `core/subject_token.py` (`SubjectTokenService`) -> recognition token lookup, issue, rotate, mark_used
- `core/session_starter.py` (`SessionStarter`) -> full session-start orchestration: access → subject → merge → token → session row → link consume

No live `SubmissionIntakeService` / `SubmissionGateway`. No response-DB write
or cross-DB orchestration service yet; response-envelope/answer services remain
future work.
