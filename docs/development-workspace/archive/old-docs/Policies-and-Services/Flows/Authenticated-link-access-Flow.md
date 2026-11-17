# Flow: Authenticated assigned link access

This flow applies when a respondent enters through an authenticated assigned link.

An authenticated assigned link is single-use, assigned to a pre-defined participant, and requires the respondent to be logged in as the user account linked to that participant identity.

The assigned link subject is always the final subject.

The logged-in user verifies access. The logged-in identity must not override the assigned subject.

## 1. Resolve link token

→ [shared/resolve-link-token.md](shared/resolve-link-token.md)

## 2. Require logged-in user

Backend checks whether the respondent is logged in.

If the respondent is not logged in, access is rejected.

The client should prompt the respondent to log in before trying to resolve the authenticated link again.

## 3. Validate link type

Backend confirms:

* `link_type = authenticated`
* `assigned_participant_id` is set
* the assigned participant exists
* the assigned participant has a linked `ProjectSubject`
* the assigned participant has a project subject identity
* the link has not already been used

If the link has already been used, access is rejected.

Authenticated assigned links are allowed for all survey visibility values.

## 4. Validate assigned identity

Backend checks the assigned project subject identity.

### Case A: identity has a linked `user_id` and it matches the logged-in user

Access is allowed.

Backend returns the respondent-facing survey schema.

No submission session is created yet.

### Case B: identity has a linked `user_id`, but it does not match the logged-in user

Access is rejected.

The logged-in account is not allowed to use this authenticated link.

### Case C: identity does not have a linked `user_id`

Access is rejected with an account-linking-required response.

The client should send the respondent to the account-linking endpoint.

The survey schema is not returned yet.

## 5. Account-linking endpoint

The client calls the account-linking endpoint using the same authenticated link token.

Backend checks:

* the link token exists
* the token hash matches
* the link is active
* the link has not expired
* `link_type = authenticated`
* `assigned_participant_id` is set
* the assigned participant exists and has a linked `ProjectSubject`
* the assigned participant has a project subject identity
* the identity does not already have a conflicting `user_id`
* the respondent is logged in
* the assigned identity email matches the logged-in user's email

If the email does not match, linking is rejected.

If the email matches, backend links the assigned identity to the logged-in `user_id`.

### Recognition token reconciliation during account linking

→ [shared/check-recognition-token.md](shared/check-recognition-token.md)

→ [shared/subject-resolution.md](shared/subject-resolution.md)

Account linking uses assigned-access subject resolution.

The assigned subject is authoritative.

If a valid browser recognition token points to a different subject, `SubjectResolver` merges the token subject into the assigned subject by setting `canonical_subject_id` on the token subject row.

→ [shared/issue-or-rotate-recognition-token.md](shared/issue-or-rotate-recognition-token.md)

The browser recognition token may be rotated during account linking so the next request resolves to the assigned subject. This is the only pre-session token-rotation path.

## 6. Retry authenticated link resolve

After successful account linking, the client returns to the normal authenticated link resolver.

This time the assigned identity has a linked `user_id` matching the logged-in user, so access proceeds.

Backend returns the respondent-facing survey schema.

No submission session is created yet.

## 7. Start submission session

The client requests to start a submission session using the authenticated assigned link.

Backend re-validates:

* the link exists and is active
* the link has not expired
* `link_type = authenticated`
* the link has not already been used
* the respondent is logged in
* the assigned participant exists and has a linked `ProjectSubject`
* the assigned project subject identity has a linked `user_id`
* the linked `user_id` matches the logged-in user
* a published survey version is available

If any check fails, session start is rejected.

Backend creates an access grant with:

* `access_method = authenticated_assigned_link`
* `project_id`
* `survey_id`
* `survey_version_id`
* `link_id`
* `assigned_subject_id`
* `is_single_use = true`

## 8. Check recognition token

→ [shared/check-recognition-token.md](shared/check-recognition-token.md)

The recognition token lookup returns only a candidate token subject. It does not decide the final subject.

## 9. Resolve subject

→ [shared/subject-resolution.md](shared/subject-resolution.md)

Authenticated links use assigned-access subject resolution.

Authority order:

1. Assigned subject
2. Logged-in user only as verification
3. Recognition token only for continuity cleanup

If the recognition token points to a different subject, `SubjectResolver` keeps the assigned subject as final and sets `canonical_subject_id` on the token subject row to point at the assigned subject.

If the logged-in user does not match the assigned identity, access must already have been rejected before this point.

## 10. Create session, consume link, and update token atomically

→ [shared/consume-single-use-link.md](shared/consume-single-use-link.md)

→ [shared/issue-or-rotate-recognition-token.md](shared/issue-or-rotate-recognition-token.md)

Backend creates the submission session using:

* the final assigned `ProjectSubject`
* the selected survey version
* the authenticated link ID
* `access_method = authenticated_assigned_link`

In the same transaction, backend:

* consumes the single-use link by setting `used_at`
* applies any canonical merge updates from subject resolution
* issues or rotates the recognition token so the browser points to the final assigned subject

If session creation fails, the link must not be consumed and the token must not be changed.

Backend returns:

* submission session token
* recognition subject token
* session metadata
