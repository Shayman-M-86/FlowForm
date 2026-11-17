# Encryption Model

## Why a Key Hierarchy

A single encryption key for all answers would mean that rotating the key, or
revoking access for one survey, requires re-encrypting everything. The solution
is a three-level hierarchy where each level is scoped narrowly and can be
rotated independently.

---

## The Three Levels

**KMS root key** — managed by AWS KMS, never leaves the KMS boundary. It is used
only to wrap and unwrap the survey branch key. FlowForm never sees the root key
in plaintext.

**Survey branch key** — one per survey, created when the survey is published.
Stored as a KMS-wrapped ciphertext in `survey_encryption_keys` alongside the KMS
key ARN and a `kms_context_version`. Unwrapping it requires a KMS Decrypt call
with the matching context. In plaintext, it is used only in-process, never
persisted.

**Session DEK** (data encryption key) — one per session, created at session
start. Wrapped locally by the survey branch key (not by KMS directly) and stored
in `response_envelopes.wrapped_session_dek`. This local wrapping is intentional:
it avoids a KMS call for every answer write and keeps per-session material
isolated. Unwrapping the DEK requires first unwrapping the branch key from KMS.

Answer payloads are encrypted with AES-GCM using the session DEK. The nonce is
stored alongside each ciphertext in `response_answers`.

---

## Why Local Wrapping for the DEK

Wrapping the session DEK with the survey branch key locally (rather than sending
each DEK to KMS directly) has two advantages:

- **Throughput** — a high-volume survey would otherwise generate one KMS API
  call per session start, hitting rate limits quickly.
- **Blast radius control** — revoking a single survey's branch key (by deleting
  or disabling it in KMS) renders all sessions under that survey unreadable,
  without touching any other survey.

---

## Key Caching

Unwrapping a branch key or a session DEK on every operation would be expensive.
The backend maintains an in-process cache with separate entries for each level:

- **Survey branch keys** — keyed by `(project_id, survey_id)`, TTL 10 minutes,
  capacity 512 entries.
- **Session DEKs** — keyed by session UUID, TTL 30 minutes, capacity 10,000
  entries.
- **Linkage keys** — the current version and a small set of prior versions are
  cached for locator derivation.

Caching is controlled by a feature flag (`encryption.key_cache_enabled`). Cache
misses fall through to KMS; there is no hard dependency on cache availability.

---

## What Is and Is Not Implemented

**Schema and infrastructure:** complete. All tables, foreign keys, and BYTEA
columns are in place. The cache registry and KMS context management are
implemented. Locator derivation (HMAC of session/answer IDs using the linkage
secret) is real.

**Service orchestration:** complete. Session start, answer save, and completion
endpoints are real — not stubs. The repository layer performs upserts using
BYTEA locators and encrypted payloads.

**Cryptographic payload operations:** pending. The AES-GCM encrypt and decrypt
calls on the answer ciphertext, and the local wrapping/unwrapping of the session
DEK with the branch key, are not yet wired into the save and read paths.

---

## Summary

| Level | Scope | Wrapped by | Stored where |
|---|---|---|---|
| KMS root key | Account-wide | KMS (never leaves) | KMS |
| Survey branch key | Per survey | KMS root key | `survey_encryption_keys` |
| Session DEK | Per session | Survey branch key (local) | `response_envelopes` |
| Answer ciphertext | Per question per session | Session DEK (AES-GCM) | `response_answers` |

---

## Loose Threads

**KMS context version tracks intent, not enforcement.** The `kms_context_version`
column exists on both `survey_encryption_keys` and `response_envelopes` for
rotation tracking, but there is no implemented rotation workflow. Incrementing
the version field without re-wrapping affected keys would silently break
decryption.

**AAD (additional authenticated data) construction is unspecified in code.** The
docs describe using survey and session identifiers as AAD for AES-GCM to prevent
ciphertext transplant attacks. This has not yet been wired into the encrypt/
decrypt path.
