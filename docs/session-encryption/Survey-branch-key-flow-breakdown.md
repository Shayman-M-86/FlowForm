# Survey Branch-Key Flow Breakdown

## What Changed

The old design treated AWS KMS as the thing that wrapped every session DEK.
Every new submission session produced a random session key, and that key was
wrapped directly by KMS before being stored in the Response DB.

The new design adds one stable survey-level branch key between KMS and session
DEKs:

```text
AWS KMS key
-> survey branch key
-> session DEK
-> encrypted answer revisions
```

KMS now protects the survey branch key. The survey branch key protects each
session DEK. Each session DEK still protects only one respondent session's
answer revisions.

## Why This Helps

This removes KMS from the normal per-session and per-answer hot path once the
survey branch key is cached. A survey can receive many sessions and many answer
saves while only needing to unwrap the survey branch key occasionally.

The Response DB also stays anonymous. It stores the opaque session locator,
the locally wrapped session DEK, and encrypted answer data. It does not need
the project ID, survey ID, KMS key ARN, KMS context version, or a foreign key
back to Core.

## Publish Flow

Publishing a survey now ensures the survey has an encryption key row in Core.

If the survey already has a key, publish reuses it. If it does not, the branch
key service generates a random survey branch key, wraps it with KMS, and stores
the wrapped branch key in `survey_encryption_keys`.

This is intentionally lazy. Survey key creation happens when the survey becomes
publishable, not when the draft is first created.

## Session Start Flow

When a respondent starts a session, Core resolves the survey and creates the
core session as before.

The response envelope step now does this:

1. Derive the anonymous session locator.
2. Load the survey encryption key row from Core.
3. Get the plaintext survey branch key from cache, or unwrap it with KMS.
4. Generate a fresh random session DEK.
5. Wrap the session DEK locally with the survey branch key.
6. Store the response envelope with `wrapped_session_dek`.

The Response DB only sees the locator and the locally wrapped session key.
KMS metadata stays in Core on the survey encryption key row.

## Answer Save Flow

When an answer is saved, the service already has the Core session and Response
DB envelope.

The encryption step now does this:

1. Load the survey encryption key row for the session's survey.
2. Get the plaintext survey branch key from cache, or unwrap it with KMS.
3. Use the survey branch key to unwrap the session DEK locally.
4. Cache the plaintext session DEK for the active session window.
5. Encrypt the answer revision with the session DEK.

On a warm worker, the answer save path should usually use cached key material
and avoid KMS entirely.

## Admin Decrypt Flow

Admin response reads use the same key chain as answer save.

For one session, the admin service resolves the session locator, loads the
response envelope, gets the survey branch key, unwraps the session DEK locally,
and decrypts the answer revisions.

For future batch decrypt work, the useful optimization is to group sessions by
survey, unwrap each survey branch key once, then locally unwrap all session
DEKs for that survey.

## Cache Shape

There are now two local worker caches:

- Survey branch key cache: holds plaintext survey branch keys for a short TTL.
- Session DEK cache: holds plaintext session DEKs for active sessions.

Neither cache is the source of truth. The source of truth is still stored data:
the KMS-wrapped survey branch key in Core and the locally wrapped session DEK
in Response.

## Mental Model

KMS is now used at the survey boundary, not the session boundary.

Session DEKs are still unique per session. Answer encryption still uses the
session DEK. The main shift is that the expensive external unwrap moves up one
level, so repeated session and answer work can stay local after the branch key
is available.
