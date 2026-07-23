# Target 11: Delete or Quarantine Stale Old Modules

Goal: remove confusion between old `services/submissions` tests/modules and new
route-facing `services/public_submissions` implementation.

Relevant docs:

* `../../core-policies.md`
* target pass reports from earlier implementation work

Likely files:

* `backend/app/services/submissions/*`
* `backend/tests/integration/core/test_submission_session_starter.py`
* `backend/tests/integration/core/test_survey_access_resolver.py`
* `backend/tests/integration/core/test_project_subject_resolver.py`

Expected direction:

* migrate or duplicate tests onto `public_submissions`
* keep old modules only if intentionally supported
* quarantine compatibility shims if deletion is not safe yet

Risk: medium. Raise to high if public route behavior depends on old modules.

Stop if hidden consumers still import old modules.
