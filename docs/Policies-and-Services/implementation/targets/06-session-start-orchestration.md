# Target 06: SessionStart Orchestration

Goal: make session start order explicit and policy-aligned.

Relevant docs:

* `../../core-policies.md`
* flow doc for each access method touched
* `../../Flows/shared/subject-resolution.md`
* `../../Flows/shared/issue-or-rotate-recognition-token.md`

Likely files:

* `backend/app/services/public_submissions/core/session_starter.py`
* `backend/app/services/public_submissions/api/session_management.py`
* `backend/app/repositories/core/submission_sessions.py`

Expected order:

1. access resolution
2. token lookup
3. subject resolution
4. token action
5. session creation
6. maybe link consumption
7. commit
8. return response and cookie data

Risk: high if token, subject merge, or link consumption changes.

Stop if transaction boundary needs redesign beyond this pass.
