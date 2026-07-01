# Auth0 Identity & Email Verification

## The Core Problem

Auth0 identifies users by a stable `sub` (subject) claim, not by email. A user
can sign up with one email, later change it inside Auth0, or be invited under a
different address entirely. FlowForm needs to handle these cases safely without
conflating "which identity am I talking to?" with "is this person allowed here?".

Additionally, Auth0's `email_verified` claim inside a token only reflects the
state at the time that token was issued — not the present moment. A user who
clicks the verification link in another tab won't appear verified to the app
until they log in again and receive a fresh token.

---

## How Identity Works

Every request is authenticated via a JWT access token. The `sub` claim from
that token is the durable key used to look up the user in FlowForm's database.
Email is treated as display/matching data, not as identity. This means:

- Users are keyed by `auth0_user_id` (the `sub`) in our DB.
- Email changes in Auth0 don't break the user's account — they flow through as
  a profile update.
- Two invitations to the same `sub` (same person, different email at different
  times) are still the same person.

---

## The Email-Verification Problem

FlowForm gates invitation acceptance on `email_verified`. This creates a
challenge: the token's claim can be stale. The solution is a two-layer
verification strategy:

1. **Local DB flag** (`users.email_verified`) — the durable source of truth,
   updated lazily and persisted so every subsequent request trusts it without a
   live call.
2. **Live Auth0 Management API check** — called when the local flag is still
   `false`. The result is cached briefly in-process to absorb refresh spam or
   multiple-tab polling, then written back to the DB when verified.

This means Auth0 is a fallback/refresh mechanism, not something every request
depends on. Once FlowForm has verified the user locally, the DB flag is the
runtime gate. Verification state settles quickly without requiring webhooks or
event streaming from Auth0.

---

## Invitation Acceptance: Two Paths

**Path 1 — Bell icon (authenticated, non-token):** The user sees a pending
invitation in the sidebar. Accepting it requires:
- Their logged-in email matches `invited_email` on the invitation, after normal
  email normalization/case handling.
- Their email is verified (local flag checked first, live Auth0 fallback if not).

**Path 2 — Email link (token-based):** The user clicks a unique token URL from
their inbox. Possessing and presenting the token *is* the proof of mailbox
ownership, so:
- Email match is still enforced (the logged-in user must match `invited_email`).
- But verification is implicitly satisfied for FlowForm's invitation flow —
  clicking a link delivered to that inbox is proof enough. The app marks
  `email_verified=True` locally and best-effort mirrors it back to Auth0 so the
  flag is consistent going forward. If that mirror fails, FlowForm's local flag
  is still the access-control decision.

---

## Summary

| Concern | Approach |
|---|---|
| User identity | Keyed by Auth0 `sub`, never email |
| Email as data | Matched for invitation gating, stored in DB |
| Verification state | DB flag (durable) + live Auth0 API (lazy fallback) |
| Token-based acceptance | Token possession substitutes for email verification |

---

## Loose Threads

**`email_verified` is tied to the user, not the email address.** Currently the
local `email_verified` flag is stored per-user (`auth0_user_id`). If a user
changes their email, the flag doesn't automatically reset — meaning a newly
registered email could inherit a verified status it hasn't earned. Worth
revisiting if email-change flows become a support concern.
