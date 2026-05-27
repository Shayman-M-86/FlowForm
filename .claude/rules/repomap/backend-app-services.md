---
paths: backend/app/services/**
---

# backend/app/services/

_Last updated: 2026-05-27 by /repomap_

Orchestration layer containing service classes (one file per domain) that coordinate repositories, enforce permissions, and manage cross-database writes. SurveyService (surveys.py) delegates reads and writes to surveys_repo, enforces project/survey-level permissions via @require_project_permission and @require_survey_permission decorators. SubmissionIntakeService (submissions.py) accepts both core_db and response_db Session arguments, resolves a pseudonymous_subject_id via SubmissionGateway (ensuring user_id never enters the response DB), and orchestrates atomic writes across both databases. Domain-specific sub-packages (e.g., access/) handle access control.
