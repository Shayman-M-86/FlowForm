# Sub-flow: Subject resolution

Shared by:

* Public slug
* General link
* Private assigned link
* Authenticated assigned link
* Authenticated assigned link account-linking

`SubjectResolver` decides the final canonical `ProjectSubject` for the submission session after `AccessResolver` has validated how the respondent entered.

Recognition tokens, assigned links, and logged-in identities can all produce candidate subjects, but only `SubjectResolver` decides which candidate becomes the final canonical subject.

---

## Service responsibilities

* `AccessResolver` validates the access method and returns the survey/link grant.
* `SubjectTokenService` looks up a browser recognition token and returns a candidate token subject.
* `SubjectResolver` chooses the final canonical subject and applies subject-side writes, including logged-in identity creation, logged-in identity attachment, and canonical merge updates.
* `SubjectTokenService` issues or rotates the browser token so it points at the final canonical subject.

---

## Inputs

`SubjectResolver` receives:

* `access_method`
* `project_id`
* `assigned_subject_id`, if the access method is assigned
* `token_subject_id`, if a valid recognition token was found
* `logged_in_user_id`, if the respondent is logged in
* the user's existing project identity subject, if one exists

Before comparing subjects, `SubjectResolver` must resolve every candidate subject to its canonical subject.

---

## Output

`SubjectResolver` returns a subject-resolution result with:

* `final_subject_id`
* `subject_source`
* whether the browser recognition token should be issued or rotated
* whether `last_used_at` should be updated on the recognition token

---

## Canonical subject rule

A submission session must always store the final canonical `ProjectSubject`.

If a candidate subject already has `canonical_subject_id` set, follow it and use the canonical subject before making comparisons.

When one subject loses to a stronger authority, merge the weaker subject into the stronger subject:

* weaker subject: set `canonical_subject_id` to the stronger subject ID
* stronger subject: remains canonical with `canonical_subject_id = null`

Do not merge a subject into itself.

Do not intentionally create canonical chains.

---

## Open-access subject resolution

Used by:

* public slug
* general link

Authority order:

1. Logged-in identity subject
2. Recognition token subject
3. New anonymous `ProjectSubject`

### Decision table

| Logged in | Token subject | Existing identity subject | Final subject | Side effect |
| --- | --- | --- | --- | --- |
| No | None | None | New anonymous subject | Issue recognition token |
| No | Valid | None | Token subject | Update token `last_used_at` |
| Yes | None | No | New subject for logged-in user | Create user identity; issue recognition token |
| Yes | Valid | No | Token subject | Attach user identity to token subject; update token `last_used_at` |
| Yes | None | Yes | Identity subject | Issue recognition token to identity subject |
| Yes | Valid, canonical same as identity | Yes | Identity subject | Update token `last_used_at`; keep token if it already points to the canonical identity subject, otherwise rotate to canonical subject |
| Yes | Valid, canonical different from identity | Yes | Identity subject | Set token subject `canonical_subject_id` to identity subject; rotate token to identity subject |

The logged-in identity subject always wins over the recognition token subject for public slug and general link access.

---

## Assigned-access subject resolution

Used by:

* private assigned link
* authenticated assigned link
* authenticated assigned link account-linking

Authority order:

1. Assigned subject
2. Recognition token only for continuity cleanup

The assigned subject is always the final subject.

### Decision table

| Assigned subject | Token subject | Final subject | Side effect |
| --- | --- | --- | --- |
| Valid | None | Assigned subject | Issue recognition token to assigned subject if needed |
| Valid | Canonical same as assigned subject | Assigned subject | Keep token if it already points to the canonical assigned subject, otherwise rotate to canonical subject |
| Valid | Canonical different from assigned subject | Assigned subject | Set token subject `canonical_subject_id` to assigned subject; rotate token to assigned subject |

---

## Authenticated assigned link verification

For authenticated assigned links, the logged-in user is used to verify access only.

The logged-in user must be linked to the assigned project subject identity.

If the logged-in user resolves to a different project subject, access is rejected.

The logged-in identity must not override the assigned subject.

If the assigned identity has no linked `user_id`, the normal authenticated link resolve is rejected with account-linking-required.

During account linking, the assigned identity may be linked to the logged-in user only after the assigned identity email matches the logged-in user's email.

After successful account linking, assigned-access subject resolution is used. If the browser token points to a different subject, the token subject is merged into the assigned subject.

---

## Token actions after subject resolution

Subject resolution decides whether a token action is required, but token mechanics are handled by [issue-or-rotate-recognition-token.md](issue-or-rotate-recognition-token.md).

Public slug and general link access may update `last_used_at` because the token can participate in open-access subject resolution.

Private and authenticated assigned links do not update `last_used_at` as recognition authority because the token does not decide the subject. If the token points to the wrong subject, or to a non-canonical subject that resolves to the assigned subject, rotate it to the assigned subject for future continuity.
