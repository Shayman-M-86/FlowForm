# Flow: Public slug access

This flow applies when a respondent starts a submission session through a public survey slug.

Public slug access is not link-based and is allowed only when the survey is public.

Public slug access does not have a separate pre-session schema-fetch phase. The respondent-facing survey schema is returned with the submission session start response.

## 1. Validate public slug access

Backend checks:

* the survey exists
* `visibility = public`
* `public_slug` matches the requested survey
* a published survey version is available

If any check fails, access is rejected.

Backend creates an access grant with:

* `access_method = public_slug`
* `project_id`
* `survey_id`
* `survey_version_id`
* no `link_id`
* no `assigned_subject_id`
* `is_single_use = false`

## 2. Check recognition token

→ [shared/check-recognition-token.md](shared/check-recognition-token.md)

The recognition token lookup returns only a candidate token subject. It does not decide the final subject.

## 3. Resolve subject

→ [shared/subject-resolution.md](shared/subject-resolution.md)

Public slug access uses open-access subject resolution.

Authority order:

1. Logged-in identity subject
2. Recognition token subject
3. New anonymous `ProjectSubject`

Backend checks whether the respondent is logged in.

If the respondent is not logged in:

* if a valid token subject exists, use that `ProjectSubject`
* if no valid token subject exists, create a new anonymous `ProjectSubject`

If the respondent is logged in, proceed to logged-in reconciliation.

→ [shared/logged-in-reconciliation.md](shared/logged-in-reconciliation.md)

If the logged-in identity subject differs from the token subject, the logged-in identity subject wins. `SubjectResolver` sets `canonical_subject_id` on the token subject row to point at the identity subject.

## 4. Issue or rotate recognition token

→ [shared/issue-or-rotate-recognition-token.md](shared/issue-or-rotate-recognition-token.md)

The browser token must point to the final canonical subject returned by `SubjectResolver`.

## 5. Create submission session

Backend creates the submission session using:

* the final canonical `ProjectSubject`
* the selected survey version
* no link ID
* `access_method = public_slug`

In the same session-start transaction, backend applies any canonical merge updates from subject resolution and any recognition-token issue, update, or rotation.

If session creation fails, the merge updates and token changes must not be persisted.

Backend returns:

* submission session token
* recognition subject token
* respondent-facing survey schema
* session metadata
