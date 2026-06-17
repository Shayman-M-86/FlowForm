# Failure, Reconciliation, and Logging Rules

## Purpose

This document captures the safety rules around cross-database writes, partial failures, logs, metrics, and operational hardening.

## Authoritative write rule

Encrypted response writes are authoritative.

Core analytics events are useful, but they must not decide whether an answer was saved. If the encrypted answer revision commits and the later analytics event fails, the answer is still saved.

## Session start failure rule

Session start should not expose a browser resume token until the required core session and response envelope both exist.

If the core session is created but response envelope creation fails before the token is exposed, the service should roll back or invalidate the partial session.

Single-use link consumption and recognition-token side effects should not be committed if encrypted session initialization fails.

## Cross-database failure rule

There is no single transaction across two PostgreSQL databases.

Services must explicitly decide:

- which write is authoritative;
- which write is secondary;
- what happens if the secondary write fails;
- what repair or reconciliation path exists.

## Reconciliation targets

Reconciliation should be able to detect and repair or flag:

- core sessions without response envelopes;
- response write success with missing analytics event;
- pending deletions;
- missing response envelopes during admin reads;
- inconsistent linkage-key versions;
- stale initialization failures.

## Delete rule

Do not claim a response is deleted until required stores have been handled.

For privacy, encrypted response material should be removed before or alongside core metadata deletion or anonymisation. If only one database operation succeeds, mark the deletion pending and retry.

## Logging rule

Never log:

- plaintext answers;
- plaintext DEKs;
- raw linkage secrets;
- browser resume tokens;
- link tokens;
- recognition tokens;
- auth cookies;
- full ciphertext values;
- full nonce values;
- KMS decrypted key material.

Errors should use safe IDs, short redacted prefixes where needed, and structured error codes.

## Observability

The system should track:

- session starts;
- envelope creation failures;
- answer saves;
- completion attempts;
- decrypt failures;
- KMS failures;
- Secrets Manager failures;
- response database failures;
- core database failures;
- reconciliation repairs;
- pending deletion retries.

Metrics should help operate the system without exposing answer content.

## Sentry and tracing

Sentry payloads, traces, and request logs must be sanitized.

Do not allow request bodies, response bodies, cookies, ciphertext blobs, key material, or answer values to be captured by default. Add explicit allowlists for safe fields rather than relying only on blocklists.

## Operational rule

Any path that decrypts answers is privileged.

Admin detail, history, export, and deletion should all go through explicit authorization and service-level decrypt/delete flows. They should not query response tables directly from API handlers.
