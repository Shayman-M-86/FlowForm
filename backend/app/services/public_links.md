# Public Link Participant Verification

This note describes the current split between public-link resolution and
participant verification.

## Core rule

Participants do not carry a separate "needs verification" flag. Verification is
resolved lazily when a participant uses an authenticated survey link.

Admin-created participants start with an email identity:

```text
ProjectParticipant
  -> ProjectSubject
  -> ProjectSubjectIdentity(identity_type="email", normalized_email=...)
```

That participant can use `general` and `private` links without becoming an
authenticated user.

## Resolve flow

`SurveyLinkService.resolve_link` is intentionally read-oriented.

It always checks:

- token exists
- link is active
- link is not expired
- single-use link has not already been used
- survey has a published version

For `general` and `private` links, no participant account linking is required.

For `authenticated` links, resolve requires:

- an authenticated actor
- `assigned_participant_id` on the link
- the assigned participant identity is already `authenticated_user`
- `participant.identity.user_id == actor.id`

If the assigned participant still has an email identity, resolve raises
`LINK_PARTICIPANT_VERIFICATION_REQUIRED`. The client should send the user to
the participant verification flow.

## Verification flow

`SurveyLinkService.verify_authenticated_link_participant` owns the token to
participant lookup for verification.

It:

- resolves the token
- checks active / not expired / not used
- returns immediately for non-`authenticated` links
- requires `assigned_participant_id`
- loads the assigned participant
- delegates identity mutation to `ParticipantService.verify_participant_for_user`

`ParticipantService.verify_participant_for_user` owns the identity upgrade.

It:

- accepts a `ProjectParticipant` and authenticated `User`
- loads the participant identity
- returns cleanly if already linked to the same user
- rejects if already linked to another user
- requires an email identity
- requires `lower(user.email) == lower(identity.normalized_email)`
- updates the existing identity in place:

```text
identity_type = "authenticated_user"
user_id = user.id
verification_status = "verified"
verified_at = now()
normalized_email = lower(user.email)
```

After verification, the client can retry `resolve_link`; the authenticated link
will pass because the participant identity now points at the logged-in user.
