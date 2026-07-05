# Target 05: TokenActionResult and Token Mechanics

Goal: apply token action after subject resolution so browser token points to
final canonical subject.

Relevant docs:

* `../../core-policies.md`
* `../../Flows/shared/issue-or-rotate-recognition-token.md`
* `../../Flows/shared/check-recognition-token.md`
* `../flow-matrix.md`

Likely files:

* `backend/app/services/public_submissions/core/subject_token.py`
* `backend/app/repositories/core/project_subject_tokens.py`
* `backend/app/services/public_submissions/core/session_starter.py`

Expected direction:

* keep valid token if it already points to final canonical subject
* rotate when browser token points to non-canonical or different subject
* issue only when no valid browser token exists
* return raw token only when browser cookie must change

Risk: high. Token rotation can affect respondent continuity.

Stop if subject resolution does not return enough token-action data.
