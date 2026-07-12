# Target 08: Authenticated Account-Linking

Goal: make authenticated link account-linking enforce link type and reconcile
browser token against assigned subject when needed.

Relevant docs:

* `../../Flows/Authenticated-link-access-Flow.md`
* `../../Flows/shared/subject-resolution.md`
* `../../Flows/shared/issue-or-rotate-recognition-token.md`

Likely files:

* `backend/app/services/public_submissions/api/survey_resolve.py`
* `backend/app/services/participants.py`
* `backend/app/services/public_submissions/core/subject_resolver.py`
* `backend/app/services/public_submissions/core/subject_token.py`
* `backend/app/api/v1/public.py`

Expected direction:

* reject non-authenticated links on account-linking endpoint
* after identity linking, reconcile browser token against assigned subject
* return or set recognition cookie only if token rotation required

Risk: high. Auth and token behavior in same pass.

Stop if response/cookie route contract needs redesign first.
