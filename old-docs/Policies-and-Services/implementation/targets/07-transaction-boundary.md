# Target 07: Transaction Boundary

Goal: ensure subject-resolution writes, token actions, session creation, and
single-use link consumption commit consistently.

Relevant docs:

* `../../core-policies.md`
* `../../Flows/shared/consume-single-use-link.md`
* `../../Flows/shared/issue-or-rotate-recognition-token.md`

Likely files:

* `backend/app/services/public_submissions/core/session_starter.py`
* `backend/app/db/error_handling`
* `backend/app/repositories/core/submission_sessions.py`
* `backend/app/repositories/public_link_repo.py`

Expected direction:

* one visible commit boundary for session-start side effects
* no persisted token or link side effect if session creation fails
* failure-path tests where practical

Risk: high. Raise to critical if migrations or destructive DB behavior appear.

Stop if current repository flush behavior prevents coherent rollback plan.
