# Failure, Reconciliation, and Logging Rules

## Purpose

This document captures the safety rules around cross-database writes, partial failures, logs, metrics, and operational hardening.

## Authoritative write rule

Encrypted response writes are authoritative.

Core analytics events are useful, but they must not decide whether an answer was saved. If the encrypted answer revision commits and the later analytics event fails, the answer is still saved.

## Session start failure rule

Session start must not expose a browser resume token until the required core session and response envelope both exist.

If response envelope creation fails before the token is exposed, the service must roll back the uncommitted core session. If a partial core session has already committed, the service must mark it abandoned and add it to reconciliation.

Single-use link consumption and recognition-token side effects must not be committed if encrypted session initialization fails.

## Cross-database failure rule

There is no single transaction across two PostgreSQL databases.

Services must explicitly decide:

- which write is authoritative;
- which write is secondary;
- what happens if the secondary write fails;
- what repair path and reconciliation path exist.

## Reconciliation targets

Reconciliation must detect these states and route each one to its remediation workflow:

- core sessions without response envelopes;
- response write success with missing analytics event;
- pending deletions;
- missing response envelopes during admin reads;
- inconsistent linkage-key versions;
- stale initialization failures.

## Delete rule

Do not claim a response is deleted until required stores have been handled.

For privacy, encrypted response material must be removed before core metadata deletion and anonymisation. Delete the response database records first, then the core records. If the response delete succeeds and the core delete fails, the deletion remains retryable and the answer data is already gone. If one database operation succeeds, mark the deletion pending and retry.

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

Errors must use safe IDs, short redacted prefixes where needed, and structured error codes.

## Observability

The system must track:

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

Metrics must help operate the system without exposing answer content.

## Sentry and tracing

Sentry payloads, traces, and request logs must be sanitized.

Do not allow request bodies, response bodies, cookies, ciphertext blobs, key material, and answer values to be captured by default. Add explicit allowlists for safe fields rather than relying only on blocklists.

## Operational rule

Any path that decrypts answers is privileged.

Admin detail, history, export, and deletion must all go through explicit authorization and service-level decrypt/delete flows. They must not query response tables directly from API handlers.
