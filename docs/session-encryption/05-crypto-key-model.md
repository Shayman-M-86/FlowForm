# Crypto and Key Model

## Purpose

This document explains the conceptual cryptography model without turning it into implementation code.

## Distinct secrets and tokens

Do not mix these values:

- access-link token: grants pre-session survey access;
- browser resume token: lets a browser continue an in-progress session;
- linkage secret: derives response-side locators;
- KEK: KMS-managed key-encryption key;
- DEK: per-session data-encryption key for answer payloads.

Each has a different job and a different storage rule.

## Browser resume token

The browser resume token is high entropy.

The browser receives the raw token in a secure cookie. The core database stores only its hash. This token is a session credential, not an encryption key and not a survey access token.

## Linkage secret

The linkage secret derives deterministic locators.

It must not live in a Postgres database. The backend retrieves the appropriate version from secret storage and uses it to derive session and answer locators.

The linkage secret needs versioning because old sessions must remain readable after rotation.

## KEK and DEK

Each response envelope gets its own DEK.

The DEK encrypts answer revisions for that session. The plaintext DEK exists only temporarily in backend memory.

The KEK lives in KMS and wraps the DEK. The response database stores the wrapped DEK, not the plaintext DEK.

## Envelope creation

When a response envelope is created:

- obtain a fresh per-session DEK;
- store only the wrapped DEK in the response envelope;
- store the crypto version and KMS context version;
- keep the plaintext DEK only as long as needed for active encryption work.

## Answer encryption

Use authenticated encryption.

The target design is AES-256-GCM. It protects answer confidentiality, detects ciphertext tampering, and detects authenticated metadata tampering.

Before encryption, answer save must validate the submitted answer against the matching frozen survey_questions node for the session’s survey_version_id.

Every answer payload must be encrypted, including values that look harmless, such as choice IDs, dates, ratings, numbers, and cleared-answer states.

## Plaintext payload

The encrypted plaintext must be a versioned payload that includes:

- payload version;
- question node ID;
- answer state;
- answer value, with null used for cleared answers.

Including the question node ID inside the encrypted payload allows the backend to verify that the decrypted payload matches the answer locator row.

## Nonces

Each encrypted revision needs a fresh nonce.

Nonce reuse with the same DEK must be treated as a serious bug. The database must help prevent accidental reuse within one envelope.

## AAD

Additional Authenticated Data must bind the encrypted revision to its database context.

AAD is not secret, but it is integrity-protected. It must include stable values such as crypto version, envelope ID, answer ID, answer locator, revision ID, and revision number.

The decrypt path must fail for every row swap and every metadata change.

## Plaintext DEK cache policy

The backend keeps the plaintext session DEK only in a local worker memory cache while the submission session is active.

The cache is an optimisation only. It is not the source of truth.

Rules:

- cache key: session locator (derive it from the resume token before any database query; the envelope ID is not known until after the response database lookup, so it cannot serve as a consistent cache key);
- cache value: plaintext DEK;
- TTL: no longer than session expiry;
- evict when the session completes, expires, is abandoned, and when the worker restarts.

On answer save:

1. Load the response envelope.
2. Check the local worker DEK cache.
3. If present, use the cached plaintext DEK.
4. If missing, call KMS `Decrypt` using `wrapped_dek`, then cache the plaintext DEK briefly.

The real source of truth is still `wrapped_dek` in the response database plus KMS decrypt when the cache misses.

Active sessions permit worker-local DEK caching. Session completion, expiry, abandonment, and worker restart evict the cached DEK.

Linkage secrets can have their own cache because they are used for deterministic locator derivation and change only through intentional rotation.

## Rotation

Different things rotate differently.

- New response envelopes use the active KEK.
- Existing envelopes keep their stored KMS key reference until rewrapped.
- New sessions use the active linkage-secret version.
- Existing sessions use their stored linkage key version.
- Crypto format changes use `crypto_version`.
- KMS context changes use `kms_context_version`.

Do not rotate any deterministic locator secret without keeping old versions readable.
