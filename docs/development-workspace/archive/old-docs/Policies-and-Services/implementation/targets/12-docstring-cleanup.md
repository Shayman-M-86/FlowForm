# Target 12: Docstring Cleanup

Goal: remove stale references to removed or renamed docs after behavior is
settled.

Relevant docs:

* docs touched by prior completed passes
* pass reports from prior completed passes

Likely files:

* `backend/app/services/public_submissions/api/session_management.py`
* `backend/app/services/public_submissions/api/survey_resolve.py`
* `backend/app/services/public_submissions/core/session_starter.py`
* `backend/app/services/public_submissions/core/subject_resolver.py`
* `backend/app/services/public_submissions/core/subject_token.py`

Expected direction:

* update references from old `service-structure.md`
* keep comments factual and short
* avoid behavior changes

Risk: low.

Do this only after behavior contracts are settled or as part of passes that
already touch the file.
