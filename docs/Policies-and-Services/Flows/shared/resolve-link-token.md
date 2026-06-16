# Sub-flow: Resolve link token

Shared by:

* General link
* Private assigned link
* Authenticated assigned link
* Authenticated assigned link account-linking

This sub-flow validates the link token and loads the link, survey, and published survey version.

It does not decide the final `ProjectSubject`.

---

## Input

The client sends the raw link token to the backend.

---

## Validation

Backend checks:

* the link token exists
* the token hash matches
* the link is active
* the link has not expired
* the link belongs to a survey
* the survey exists
* a published survey version is available

If any check fails, access is rejected.

---

## Output

Returns the link and access context needed by the caller, including:

* `project_id`
* `survey_id`
* `survey_version_id`
* `link_id`
* `link_type`
* `assigned_participant_id`, if present
* `assigned_subject_id`, if present
* `used_at`

The caller must still validate that the link type is allowed for the requested flow and survey visibility.
