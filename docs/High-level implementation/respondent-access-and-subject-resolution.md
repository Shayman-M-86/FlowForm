# Respondent Access & Subject Resolution

## The Two-Step Model

When a respondent arrives at a survey, two separate things happen in sequence:

1. **Access validation** — can this person reach this survey at all?
2. **Subject resolution** — who *is* this person within this project?

These are intentionally kept separate. `AccessResolver` handles step one and
returns an access grant. `SubjectResolver` handles step two and returns the
stable `ProjectSubject` that the submission session will be attached to.

---

## Survey Visibility & Link Types

**Visibility** controls which entry methods are permitted:

- `public` — reachable via public slug URL or any link type.
- `link_only` — requires a link; public slug browsing is blocked.
- `private` — requires a participant-assigned link; general links are blocked.

**Link type** controls who can use the link and how the subject is resolved:

- `general` — reusable, no pre-assigned participant. Subject comes from the
  open-access waterfall.
- `private` — single-use, participant pre-assigned. Assigned subject always wins.
- `authenticated` — single-use, participant pre-assigned, and the respondent must
  be logged in as the assigned participant before access is granted.

---

## Subject Resolution: The Waterfall

For **open-access** entries (public slug, general link), the subject is resolved
in priority order:

1. Logged-in identity subject (if the user is signed in and has a project identity)
2. Recognition token subject (if the browser has a valid token for this project)
3. New anonymous `ProjectSubject` (created on the spot)

For **assigned-access** entries (private, authenticated), the assigned
participant's subject always wins regardless of any token or logged-in state.

---

## Recognition Tokens

A recognition token is a browser cookie scoped to a single project. It lets a
returning respondent be recognised as the same `ProjectSubject` across visits
without requiring authentication.

Key properties:

- Only the hash is stored; the raw token never touches the database.
- A token is a *candidate*, not an authority. `SubjectResolver` decides whether
  it wins, gets merged, or gets rotated.
- For assigned-access links, the token is checked only for continuity cleanup
  (to reconcile a stale browser token to the assigned subject).
- Tokens are issued or rotated at session start, after the final subject is known.

---

## Subject Merging

When a stronger authority wins over a weaker candidate subject (e.g. a logged-in
identity beats an anonymous token subject), the weaker subject is not deleted. It
is marked with `canonical_subject_id` pointing to the winner. Future lookups of
the old subject resolve through to the canonical one.

Chains are not allowed — resolution always walks to the final canonical before
comparing or merging.

---

## Transactional Consistency

Session creation, subject-resolution effects (identity writes, canonical merges),
recognition-token actions, and single-use link consumption all commit together.
If session creation fails, none of the side effects are persisted.
