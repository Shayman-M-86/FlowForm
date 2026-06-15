---
paths: backend/app/domain/**
---

# backend/app/domain/

_Last verified: 2026-06-15_

Domain policy + typed errors. No HTTP here. Routes/services call domain
functions; do not duplicate access/survey/link/auth/session policy inline.

Rules = small `ensure_*` guards:

- pass -> `None`
- fail -> structured `AppError` from `errors.py`
- usual -> pure ORM/domain-object check, often mirrors DB constraint
- rare lookup -> narrow repository call, like `submission_access_rules.py`

Use domain for durable policy names + real concepts. Avoid service-local adapter
objects when concept belongs here. `permissions.py` owns frozen permission sets +
shared `PERMISSIONS`.
