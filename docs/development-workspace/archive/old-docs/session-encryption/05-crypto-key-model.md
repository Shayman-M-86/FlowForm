# Crypto and Key Model

## Purpose

This document explains the conceptual cryptography model without turning it into implementation code.

## Distinct secrets and tokens

Do not mix these values:

- access-link token: grants pre-session survey access;
- browser resume token: lets a browser continue an in-progress session;
- linkage secret: derives response-side locators;
- KMS key: protects survey branch keys;
- survey branch key: per-survey key that wraps session DEKs locally;
- session DEK: per-session data-encryption key for answer payloads.

Each has a different job and a different storage rule.

## Browser resume token

The browser resume token is high entropy.

The browser receives the raw token in a secure cookie. The core database stores only its hash. This token is a session credential, not an encryption key and not a survey access token.

## Linkage secret

The linkage secret derives deterministic locators.

It must not live in a Postgres database. The backend retrieves the appropriate version from secret storage and uses it to derive session and answer locators.

The linkage secret needs versioning because old sessions must remain readable after rotation.

## Key hierarchy

The encryption hierarchy has three levels:

```text
AWS KMS key
-> survey branch key (one per survey, stored in Core DB)
-> session DEK (one per session, stored in Response DB)
-> encrypted answer revisions
```

KMS protects the survey branch key. The survey branch key locally wraps session DEKs using AES-256-GCM. Each session DEK encrypts answer revisions for one respondent session.

The survey branch key is created lazily at survey publish time. It is stored KMS-wrapped in the `survey_encryption_keys` table in Core DB with the KMS key ARN and KMS context version.

The session DEK is created at session start. It is wrapped locally with the survey branch key and stored as `wrapped_session_dek` in the response envelope. The Response DB never sees KMS metadata.

Plaintext key material (survey branch keys and session DEKs) exists only temporarily in backend worker memory caches.

## Envelope creation

When a response envelope is created:

- load the survey encryption key row from Core DB;
- unwrap the survey branch key (from worker cache, or via KMS on cache miss);
- generate a fresh 32-byte session DEK;
- wrap the session DEK locally with AES-256-GCM using the survey branch key;
- store the wrapped session DEK and crypto version in the response envelope;
- cache the plaintext session DEK for the active session window.

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

Additional Authenticated Data is not secret, but it is integrity-protected.

There are two AAD contexts:

**Session DEK wrap AAD** binds the locally wrapped session DEK to its session context. It includes crypto version, project ID, survey ID, session ID, and session locator.

**Answer revision AAD** binds each encrypted revision to its database row. It includes stable values such as crypto version, envelope ID, answer ID, answer locator, revision ID, and revision number.

**KMS encryption context** binds the survey branch key to its survey. It includes purpose (`survey_branch_key`), project ID, survey ID, and KMS context version.

The decrypt path must fail for every row swap and every metadata change.

## Cache policy

There are two worker-local caches. Neither is the source of truth.

### Survey branch key cache

- cache key: survey encryption key row ID;
- cache value: plaintext survey branch key;
- TTL: 1 hour;
- evict on worker restart.

### Session DEK cache

- cache key: session ID;
- cache value: plaintext session DEK;
- TTL: no longer than session expiry;
- evict when the session completes, expires, is abandoned, and when the worker restarts.

On answer save:

1. Load the response envelope.
2. Check the session DEK cache.
3. If present, use the cached plaintext session DEK.
4. If missing, load the survey encryption key from Core, unwrap the survey branch key (from cache or KMS), locally unwrap the session DEK using the survey branch key, then cache the plaintext session DEK.

The source of truth is the KMS-wrapped survey branch key in Core DB and the locally wrapped session DEK in Response DB.

On a warm worker, the answer save path typically uses cached key material and avoids KMS entirely.

Linkage secrets can have their own cache because they are used for deterministic locator derivation and change only through intentional rotation.

## Rotation

Different things rotate differently.

- KMS key rotation uses AWS built-in rotation; KMS handles multi-version decrypt automatically for existing survey branch keys.
- New surveys get branch keys wrapped with the current KMS key.
- Existing survey branch keys remain on their original KMS key version.
- Session DEKs are locally wrapped and do not reference KMS directly, so KMS rotation does not affect them.
- New sessions use the active linkage-secret version.
- Existing sessions use their stored linkage key version.
- Crypto format changes use `crypto_version`.
- KMS context changes use `kms_context_version` on the survey encryption key row.

Do not rotate any deterministic locator secret without keeping old versions readable.
