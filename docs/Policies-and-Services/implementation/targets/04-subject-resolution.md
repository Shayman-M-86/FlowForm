# Target 04: SubjectResolutionResult

Goal: make `SubjectResolver` choose final canonical subject and return token
action instructions.

Relevant docs:

* `../../core-policies.md`
* `../../Flows/shared/subject-resolution.md`
* `../../Flows/shared/logged-in-reconciliation.md`
* `../flow-matrix.md`

Likely files:

* `backend/app/services/public_submissions/core/subject_resolver.py`
* `backend/app/services/results.py`
* `backend/app/repositories/core/project_subject_identities.py`
* `backend/app/repositories/core/project_subjects.py`

Expected direction:

* resolve every candidate to canonical subject before comparison
* implement open-access resolution for public slug and general link
* implement assigned-access resolution for private and authenticated links
* return keep, issue, rotate, or mark-used token instruction
* keep assigned subjects authoritative for assigned-link flows

Risk: high. Canonical merge logic and identity attachment affect stored subject
history.

Stop if access grant still lacks required subject/access context.
