# Flow: Private assigned link access

This flow applies when a respondent enters through a private assigned link.

A private link is single-use, assigned to a pre-defined participant, and resolves to that participant's `ProjectSubject`.

The assigned subject is always the final subject.

## 1. Resolve link token

→ [shared/resolve-link-token.md](shared/resolve-link-token.md)

## 2. Validate link type

Backend confirms:

* `link_type = private`
* `assigned_participant_id` is set
* the assigned participant exists
* the assigned participant has a linked `ProjectSubject`
* the link has not already been used

If the link has already been used, access is rejected.

## 3. Validate survey visibility

Private assigned links are allowed for all survey visibility values:

* `public`
* `link_only`
* `private`

## 4. Return survey schema

Once the link and survey are valid, backend returns the respondent-facing survey schema.

No submission session is created yet.

The link is not consumed just because the schema was fetched.

## 5. Start submission session

The client requests to start a submission session using the private link.

Backend re-validates:

* the link exists and is active
* the link has not expired
* `link_type = private`
* `assigned_participant_id` is set
* the assigned participant exists and has a linked `ProjectSubject`
* the link has not already been used
* a published survey version is available

Backend creates an access grant with:

* `access_method = private_link`
* `project_id`
* `survey_id`
* `survey_version_id`
* `link_id`
* `assigned_subject_id`
* `is_single_use = true`

## 6. Check recognition token

→ [shared/check-recognition-token.md](shared/check-recognition-token.md)

The recognition token lookup returns only a candidate token subject. It does not decide the final subject.

## 7. Resolve subject

→ [shared/subject-resolution.md](shared/subject-resolution.md)

Private links use assigned-access subject resolution.

Authority order:

1. Assigned subject
2. Recognition token only for continuity cleanup

If the recognition token points to a different subject, `SubjectResolver` keeps the assigned subject as final and sets `canonical_subject_id` on the token subject row to point at the assigned subject.

## 8. Create session, consume link, and update token atomically

→ [shared/consume-single-use-link.md](shared/consume-single-use-link.md)

→ [shared/issue-or-rotate-recognition-token.md](shared/issue-or-rotate-recognition-token.md)

Backend creates the submission session using:

* the final assigned `ProjectSubject`
* the selected survey version
* the private link ID
* `access_method = private_link`

In the same transaction, backend:

* consumes the single-use link by setting `used_at`
* applies any canonical merge updates from subject resolution
* issues or rotates the recognition token so the browser points to the final assigned subject

If session creation fails, the link must not be consumed and the token must not be changed.

Backend returns:

* submission session token
* recognition subject token
* session metadata
