# Sub-flow: Check recognition token

Shared by:

* Public slug
* General link
* Private assigned link
* Authenticated assigned link
* Authenticated assigned link account-linking

This sub-flow performs token lookup only.

It does not decide the final `ProjectSubject`.

It does not merge subjects.

It does not issue or rotate tokens.

Those decisions belong to [subject-resolution.md](subject-resolution.md) and [issue-or-rotate-recognition-token.md](issue-or-rotate-recognition-token.md).

---

## Input

The request may contain a raw recognition token from the respondent's browser.

The backend also knows the current `project_id` from the validated access method.

---

## Validation

Backend checks whether the request contains a valid recognition token for the same project.

A token is valid while:

* `expires_at` is in the future
* `revoked_at` is null
* the token belongs to the same `project_id`
* the raw token hash matches the stored token hash

If the token is missing, malformed, expired, revoked, hash-mismatched, or scoped to another project, no token subject is resolved.

---

## Output

The lookup result includes:

* whether a token was present
* whether the token was valid
* `token_id`, if valid
* `token_subject_id`, if valid
* `canonical_token_subject_id`, if valid
* reason for no valid token, if useful for logging

The returned token subject is only a candidate.

The final subject is decided by [subject-resolution.md](subject-resolution.md).
