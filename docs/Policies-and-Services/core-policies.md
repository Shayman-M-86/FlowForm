# Core Policies

Platform-level rules that cut across respondent access, subject resolution, recognition tokens, and submission sessions.

---

## Survey visibility

A survey's `visibility` field controls how respondents can reach it.

| Value | Meaning |
| --- | --- |
| `public` | Browsable by anyone with the public URL. Requires a `public_slug`. General links also work. |
| `link_only` | Not publicly browsable. A general unassigned link is sufficient. No participant pre-assignment is required. |
| `private` | Requires a participant-assigned link: `private` or `authenticated`. General links and public slug access are blocked. Never has a public slug. |

**Enforced at:**

* link creation/update: `SurveyLinkService._ensure_link_allowed_by_visibility`
* link resolve and session start: `submission_access_rules.ensure_access_grant_permitted`
* database constraints: `ck_surveys_slug_requires_public_visibility`

---

## Survey link types

A link's `link_type` controls who can use it, whether a participant must be pre-defined before link creation, and which authority is allowed to decide the session's `ProjectSubject`.

| Type | Reusable | Requires pre-defined participant | Final subject authority |
| --- | --- | --- | --- |
| `general` | Yes | No | `SubjectResolver` open-access rules: logged-in identity subject if present, otherwise recognition token subject, otherwise new anonymous `ProjectSubject` |
| `private` | No, single-use | Yes - `assigned_participant_id` must be set | Assigned participant's `ProjectSubject` |
| `authenticated` | No, single-use | Yes - `assigned_participant_id` must be set, and the assigned identity must be linked to the logged-in user before access | Assigned participant's `ProjectSubject`, after authenticated identity verification |

### Key constraints

* `general` links must have `assigned_participant_id = null`.
* `private` and `authenticated` links must have `assigned_participant_id` set.
* A `general` link cannot be created against a `private` survey.
* `private` and `authenticated` links are allowed for all survey visibility values.
* `used_at` can only be set on assigned links.
* `assignment_source` records how the participant was attached to the link, but does not affect access rules.

---

## Access validation vs subject resolution

Access validation and subject resolution are separate steps.

Public slug access starts a submission session directly. It does not use a separate pre-session schema-fetch phase.

Link-based access may return the respondent-facing survey schema after link validation and before session start. No subject is resolved and no submission session is created during that pre-session link resolve.

### Access validation

`AccessResolver` decides whether the respondent is allowed to reach the survey through the requested access method.

It returns an access grant containing:

* `access_method`
* `project_id`
* `survey_id`
* `survey_version_id`
* `link_id`, if the entry method is link-based
* `assigned_subject_id`, if the entry method is assigned
* whether authentication is required
* whether the link is single-use

`AccessResolver` must not decide the final `ProjectSubject` except for returning the assigned subject candidate when the access method is assigned.

### Subject resolution

`SubjectResolver` is the only service that decides the final `ProjectSubject` for a submission session.

Recognition tokens may identify a candidate subject, but they do not decide authority.

`SubjectResolver` applies subject-side writes from resolution, including logged-in identity creation, logged-in identity attachment, and canonical merge updates.

When a stronger authority beats a weaker subject, `SubjectResolver` records the merge by setting `canonical_subject_id` on the weaker `project_subjects` row.

Before comparing two subjects, all candidate subject IDs must be resolved to their canonical subject IDs.

---

## Subject authority rules

### Public slug and general link

Public slug and general link access use open-access subject resolution.

Authority order:

1. Logged-in identity subject
2. Recognition token subject
3. New anonymous `ProjectSubject`

If the respondent is logged in and has an existing project identity, that identity subject wins over the recognition token subject.

If the token subject is different from the logged-in identity subject:

* keep the logged-in identity subject as canonical
* set `canonical_subject_id` on the token subject row to the identity subject ID
* issue or rotate the recognition token so the browser points to the identity subject

### Private assigned link

Private assigned links use assigned-access subject resolution.

Authority order:

1. Assigned link subject
2. Recognition token only for continuity cleanup

The assigned subject is always the final subject.

If a recognition token points to a different subject:

* keep the assigned subject as canonical
* set `canonical_subject_id` on the token subject row to the assigned subject ID
* issue or rotate the recognition token so the browser points to the assigned subject

### Authenticated assigned link

Authenticated assigned links also use assigned-access subject resolution.

Authority order:

1. Assigned link subject
2. Logged-in user only as verification
3. Recognition token only for continuity cleanup

The assigned subject is always the final subject.

The logged-in user must be linked to the assigned subject identity. If the logged-in user resolves to a different subject, access is rejected. The logged-in identity must not override the assigned-link subject.

If the assigned identity has no linked `user_id`, access is rejected with an account-linking-required response. The account-linking endpoint may link the assigned identity to the logged-in user after validating the assigned email matches the logged-in user's email.

---

## Recognition token policy

A `project_subject_token` recognises a returning browser within the same project. It links the browser back to a stable `ProjectSubject` without requiring authentication.

Only the token hash is stored. The raw token is never stored.

### Purpose

Recognition tokens are for subject continuity only.

They do not grant survey access by themselves. The respondent must still enter through a valid access method, such as:

* public slug
* general link
* private assigned link
* authenticated assigned link

### Token lookup

The recognition-token service checks whether a request contains a valid recognition token for the same project.

A token is valid only while:

* `expires_at` is in the future
* `revoked_at` is null
* the token belongs to the same `project_id`
* the raw token hash matches the stored token hash

Expired, revoked, missing, malformed, hash-mismatched, or wrong-project tokens are ignored.

Token lookup returns a candidate token subject only. It does not decide the final subject.

### Issuing and rotating tokens

Recognition tokens are normally issued or rotated at session start, after `SubjectResolver` has chosen the final canonical subject.

If the final subject does not already have a valid browser token, issue a new one.

This applies to:

* public slug access
* general link access
* private assigned link access
* authenticated assigned link access

The token is scoped to one `project_id`, not one survey. A token issued during survey A can recognise the same subject in survey B within the same project.

### Account-linking exception

Authenticated assigned link account-linking may rotate the browser recognition token before session start.

This is allowed only after:

* the authenticated link token has been validated
* the respondent is logged in
* the assigned identity email matches the logged-in user's email
* the assigned identity has been linked to the logged-in `user_id`

If a browser recognition token points to a different subject during account linking, `SubjectResolver` merges that token subject into the assigned subject and rotates the browser token to the assigned subject.

---

## Token use by access method

| Access method | Token lookup | Update `last_used_at` | Subject source |
| --- | --- | --- | --- |
| Public slug | Yes | Yes, if the token participates in open-access subject resolution | Logged-in identity subject, otherwise token subject, otherwise new anonymous subject |
| General link | Yes | Yes, if the token participates in open-access subject resolution | Logged-in identity subject, otherwise token subject, otherwise new anonymous subject |
| Private assigned link | Yes, for continuity cleanup | No | Assigned subject |
| Authenticated assigned link | Yes, for continuity cleanup | No | Assigned subject, after logged-in identity verification |

For private and authenticated assigned links, the recognition token is not the authority for subject resolution. It is checked only so the browser can be reconciled to the assigned subject for future continuity.

---

## Canonical subject merge policy

Merging is recorded directly on `project_subjects`.

When Subject A is merged into Subject B:

* Subject A gets `canonical_subject_id = SubjectB.id`
* Subject B remains canonical with `canonical_subject_id = null`
* future lookups of Subject A must resolve to Subject B

Do not create a merge if both candidate subjects already resolve to the same canonical subject.

Do not point a subject at itself. The DB constraint `ck_project_subjects_not_self_canonical` prevents this.

Do not create canonical chains intentionally. If a candidate subject already has a `canonical_subject_id`, resolve it first and use the final canonical subject.

---

## Single-use link policy

`private` and `authenticated` links are single-use.

A single-use link is consumed by setting `used_at`.

Consumption must happen atomically with submission session creation.

If session creation fails, the link must not be consumed.

General links are reusable and are never consumed.

---

## Session-start persistence policy

At session start, submission session creation, subject-resolution effects, and recognition-token actions must commit consistently.

If session creation fails, canonical merge updates and recognition-token changes from that session-start attempt must not be persisted.

For single-use links, the same transaction also includes consuming the link by setting `used_at`.

---

## Shared flow documents

* [Resolve link token](Flows/shared/resolve-link-token.md)
* [Check recognition token](Flows/shared/check-recognition-token.md)
* [Subject resolution](Flows/shared/subject-resolution.md)
* [Logged-in reconciliation](Flows/shared/logged-in-reconciliation.md)
* [Issue or rotate recognition token](Flows/shared/issue-or-rotate-recognition-token.md)
* [Consume single-use link](Flows/shared/consume-single-use-link.md)
