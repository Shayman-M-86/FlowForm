# Sub-flow: Issue or rotate recognition token

Shared by:

* Public slug
* General link
* Private assigned link
* Authenticated assigned link
* Authenticated assigned link account-linking

This sub-flow updates the browser's recognition token after `SubjectResolver` has selected the final canonical `ProjectSubject`.

It does not decide the final subject.

---

## Inputs

The backend has:

* `project_id`
* final canonical `project_subject_id`
* recognition token lookup result, if one exists
* token action returned by [subject-resolution.md](subject-resolution.md)

---

## Rules

The browser recognition token must point to the final canonical subject.

If there is no valid browser token, issue a new token for the final subject.

If the browser token already points to the final canonical subject, keep it.

If the browser token points to a non-canonical subject that resolves to the final canonical subject, rotate it so future token lookup points directly to the canonical subject.

If the browser token points to a different subject, rotate it:

* revoke or supersede the old browser token
* issue a new raw token for the final canonical subject
* store only the new token hash
* return the raw token to the client once

---

## `last_used_at`

Update `last_used_at` only when the token participated in open-access subject resolution:

* public slug
* general link

Do not update `last_used_at` as recognition authority for:

* private assigned link
* authenticated assigned link

For assigned links, the token is checked only for reconciliation and continuity cleanup. It does not decide the session subject.

---

## Normal timing

Recognition tokens are normally issued or rotated at session start, after subject resolution and before the response is returned to the client.

For every session-start path, token updates should be committed consistently with session creation. If session creation fails, the token update should roll back.

For single-use links, token updates should also be committed consistently with link consumption.

---

## Account-linking timing exception

Authenticated assigned link account-linking may rotate the browser recognition token before session start.

This is allowed only after the account-linking endpoint has validated:

* authenticated link token
* logged-in user
* assigned identity email equals logged-in user email
* assigned identity has been linked to the logged-in `user_id`

This prevents the next authenticated link resolve from seeing the old browser token as a conflicting subject.
