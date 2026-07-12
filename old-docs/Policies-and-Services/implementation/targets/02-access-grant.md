# Target 02: AccessGrant Contract

Goal: make access result carry explicit access context instead of making later
services reinterpret ORM shape.

Relevant docs:

* `../../core-policies.md`
* `../../Flows/shared/resolve-link-token.md`
* flow doc for entry method under test

Likely files:

* `backend/app/services/results.py`
* `backend/app/services/public_submissions/core/access_resolver.py`
* `backend/app/domain/submission_access_rules.py`
* access-resolution and session-start tests

Expected contract fields:

* `access_method`
* `project_id`
* `survey_id`
* `survey_version_id`
* `link_id`
* `assigned_subject_id`
* authentication requirement
* single-use status

Risk: medium. Raise to high if auth behavior changes.

Stop if subject resolution or token mechanics must be redesigned in this pass.
