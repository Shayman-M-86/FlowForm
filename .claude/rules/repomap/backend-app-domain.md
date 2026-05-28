---
paths: backend/app/domain/**
---

# backend/app/domain/

_Last updated: 2026-05-27 by /repomap_

Pure business-logic layer containing rule functions and typed domain errors — no SQLAlchemy imports or HTTP concerns. Files like `survey_rules.py` and `access_rules.py` contain guard functions (e.g. `ensure_visibility_slug_coherent`) that mirror DB CHECK constraints and raise structured `AppError` subclasses defined in `errors.py`. `permissions.py` defines frozen dataclass permission sets (`ProjectPermissionSet`, `SurveyPermissionSet`, `SubmissionPermissionSet`) collected under a single `PERMISSIONS` singleton, which is imported by the schema limits layer.
