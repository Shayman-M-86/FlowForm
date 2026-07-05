# Target 09: Response and Cookie Contract

Goal: make docs, route behavior, service return values, response schema, and
cookie behavior agree.

Relevant docs:

* `../../core-policies.md`
* `../../Flows/Public-slug-flow.md`
* `../../Flows/General-Link-Flow.md`
* `../../Flows/Private-link-access-Flow.md`
* `../../Flows/Authenticated-link-access-Flow.md`

Likely files:

* `backend/app/schema/api/responses/submission_sessions.py`
* `backend/app/api/v1/public.py`
* `backend/app/services/public_submissions/api/session_management.py`
* `backend/app/services/public_submissions/core/session_starter.py`
* OpenAPI export tests

Decision needed:

* tokens in secure cookies or response body
* whether survey schema belongs in session start response now
* route response shape for link pre-session schema resolve

Risk: medium. Raise to high if auth/cookie security behavior changes.

Stop if API contract decision needs user approval.
