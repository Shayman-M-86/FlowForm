# Failure, Reconciliation, and Logging Rules

## Purpose

This document captures the safety rules around cross-database writes, partial failures, logs, metrics, and operational hardening.

## Authoritative write rule

Encrypted response writes are authoritative.

Core analytics events are useful, but they must not decide whether an answer was saved. If the encrypted answer revision commits and the later analytics event fails, the answer is still saved.

## Session start failure rule

Session start must not expose a browser resume token until the required core session and response envelope both exist.

Single-use link consumption and recognition-token side effects must not be committed if encrypted session initialization fails.

The word `abandoned` is reserved for a committed core session that can no longer be safely resumed. Do not use it for an uncommitted session-start attempt that can still be rolled back.

### Session start partial states

Three failure states matter because core and response are separate databases:

**Response envelope creation fails before core commit.** The core session, single-use link consumption, and recognition-token side effects are still uncommitted. The service rolls back the core transaction. No data persists in either database. Do not mark a session `abandoned` in this path because there is no durable core session to mark.

**Response envelope committed, core commit fails.** The response envelope exists but no core session references it. The service must not return the browser resume token and must not cache the plaintext DEK. It attempts immediate compensating deletion of the orphan envelope by session locator. If cleanup fails, the orphan envelope is inert — it contains only a wrapped DEK and a session locator with no corresponding core session — and is routed to reconciliation for later removal.

**Core session committed, response envelope missing.** The core session exists but cannot be used because encrypted response initialization did not complete. Reconciliation must mark the core session `abandoned` and leave it rejected by current-session loading. The repair path must not create a replacement envelope for the committed session unless a future migration can prove the original response-side write never partially succeeded.

## Cross-database failure rule

There is no single transaction across two PostgreSQL databases.

Services must explicitly decide:

- which write is authoritative;
- which write is secondary;
- what happens if the secondary write fails;
- what repair path and reconciliation path exist.

## Reconciliation targets

Reconciliation must detect these states and route each one to its remediation workflow:

- core sessions without response envelopes, which must be marked `abandoned`;
- response envelopes without core sessions (orphan envelopes from failed core commits);
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
