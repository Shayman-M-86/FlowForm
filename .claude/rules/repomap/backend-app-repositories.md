---
paths: backend/app/repositories/**
---

# backend/app/repositories/

_Last verified: 2026-06-15_

Data-access layer. Free functions, not repository classes. Usual shape:

- `Session` in, ORM row/list/tuple out
- reads -> `select()`, `db.scalar()`, `db.scalars()`, sometimes `selectinload()`
- writes -> `db.add()` / mutate / `db.delete()` + `flush_with_err_handle()`
- commits/transactions -> service layer, not repo layer
- policy/auth decisions -> domain/services, not repos

Most modules map to one entity/workflow. New subject/session repos live under
`repositories/core/` (`project_subjects`, identities, tokens, participants,
`submission_sessions`). No response-DB repository layer exists yet; response
side currently has ORM/schema/error-handling only. `response_stores_repo.py`
manages core-side response-store metadata, not response DB writes.

Special cases OK when local to persistence: `users_repo.create_user()` retries
`public_id` collisions; `public_link_repo.py` owns token generation/hash lookup;
`submission_sessions.py` owns browser session token generation/hash.
