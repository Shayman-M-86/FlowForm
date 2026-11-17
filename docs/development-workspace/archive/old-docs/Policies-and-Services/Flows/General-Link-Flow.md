# Flow: General link access

This flow applies when a respondent enters through a general survey link.

A general link is reusable, unassigned, and does not require a pre-defined participant.

Allowed for:

* `public` surveys
* `link_only` surveys

Blocked for:

* `private` surveys

## 1. Resolve link token

→ [shared/resolve-link-token.md](shared/resolve-link-token.md)

## 2. Validate link type

Backend confirms:

* `link_type = general`
* `assigned_participant_id = null`
* the link is reusable
* `used_at` is null or ignored for general links

General links are never consumed.

## 3. Validate survey visibility

Allowed:

* `public`
* `link_only`

Blocked:

* `private`

If the survey is private, access is rejected.

## 4. Return survey schema

Once the link and survey are valid, backend returns the respondent-facing survey schema.

No submission session is created yet.

No subject is resolved yet.

## 5. Start submission session

The client requests to start a submission session using the general link.

Backend re-validates:

* the link exists and is active
* the link has not expired
* `link_type = general`
* `assigned_participant_id = null`
* the survey visibility allows general link access
* a published survey version is available

Backend creates an access grant with:

* `access_method = general_link`
* `project_id`
* `survey_id`
* `survey_version_id`
* `link_id`
* no `assigned_subject_id`
* `is_single_use = false`

## 6. Check recognition token

→ [shared/check-recognition-token.md](shared/check-recognition-token.md)

The recognition token lookup returns only a candidate token subject. It does not decide the final subject.

## 7. Resolve subject

→ [shared/subject-resolution.md](shared/subject-resolution.md)

General link access uses open-access subject resolution.

Authority order:

1. Logged-in identity subject
2. Recognition token subject
3. New anonymous `ProjectSubject`

If the respondent is logged in, proceed to logged-in reconciliation.

→ [shared/logged-in-reconciliation.md](shared/logged-in-reconciliation.md)

If the logged-in identity subject differs from the token subject, the logged-in identity subject wins. `SubjectResolver` sets `canonical_subject_id` on the token subject row to point at the identity subject.

## 8. Issue or rotate recognition token

→ [shared/issue-or-rotate-recognition-token.md](shared/issue-or-rotate-recognition-token.md)

The browser token must point to the final canonical subject returned by `SubjectResolver`.

## 9. Create submission session

Backend creates the submission session using:

* the final canonical `ProjectSubject`
* the selected survey version
* the general link ID
* `access_method = general_link`

In the same session-start transaction, backend applies any canonical merge updates from subject resolution and any recognition-token issue, update, or rotation.

If session creation fails, the merge updates and token changes must not be persisted.

Backend returns:

* submission session token
* recognition subject token
* session metadata
