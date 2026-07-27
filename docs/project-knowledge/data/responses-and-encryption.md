---
title: Responses and encryption
aliases: ["Responses and encryption"]
document_type: domain
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-27
tags: [security]
related_code:
  - "../../../backend/app/crypto/"
  - "../../../backend/app/cache/crypto.py"
  - "../../../backend/app/repositories/response/"
  - "../../../backend/app/schema/orm/core/submission_answer_slot.py"
  - "../../../backend/app/schema/orm/core/submission_session.py"
  - "../../../backend/app/schema/orm/response/"
  - "../../../backend/app/services/public_submissions/core/actions/"
  - "../../../backend/app/services/public_submissions/core/session_loader.py"
  - "../../../backend/app/services/admin_results/"
  - "../../../backend/app/db/manager.py"
  - "../../../infra/database/init/schema/flowform_response_db_schema_v4.sql"
related_docs:
  - "Data knowledge"
  - "Respondent access and continuity"
  - "Submissions"
  - "Security model"
  - "Trust boundaries"
---

# Responses and encryption

FlowForm keeps identity-bearing and survey metadata in a core store while the
response store contains encrypted answer material addressed through derived
opaque locators. This is data minimisation at rest, not a protection boundary
against a compromised backend process: the backend opens both stores and has
access to the linkage and decryption material needed for authorized results.

This domain begins after respondent access and subject resolution. It owns the
encrypted response envelope, current encrypted answers, session cryptographic
context, authorized decryption, and response-first deletion. It does not decide
who may enter a survey or which subject represents them.

## Storage boundary

The two stores intentionally know different things:

| Core store | Response store |
| --- | --- |
| Project, survey, and frozen version | Opaque response envelope |
| Subject, link, and session metadata | Wrapped per-session key |
| Browser resume-token hash | Current encrypted answer rows |
| Answer slots with question identity | Opaque session and answer locators |
| Wrapped survey key and KMS metadata | Ciphertext, nonce, and mutation identifier |

The response-side ORM and SQL schema model response envelopes and answers rather
than users, projects, surveys, subjects, or core foreign keys. A response
envelope carries an opaque session locator, a linkage-key version, and wrapped
session-key material. Answer rows carry an opaque answer locator, ciphertext,
nonce, and limited response metadata. Core records provide the identity,
lifecycle, and answer-slot context used to derive those locators. There is no
database foreign key or SQL join from response data back to core records.

The browser receives a raw resume token for one submission session, while the
core store retains only its hash. This token is a session credential; it is not
a survey-link token, recognition token, linkage key, or encryption key.

## Locator and key model

A versioned linkage key derives deterministic, pseudonymous locators. A session
locator is derived from the core session ID. An answer locator is derived from
the corresponding core answer-slot ID. Existing sessions retain the linkage-key
version needed to reproduce their locators after the active key changes.

Locator derivation is separate from answer encryption:

```text
core session ID -- versioned linkage key --> response envelope locator

core answer slot ID -- same key version ---> encrypted answer locator
```

The encryption hierarchy has three levels. AWS KMS wraps a per-survey branch
key stored in core data. That survey key wraps a fresh per-session data
encryption key stored in the response envelope. The session key encrypts every
current answer value for that session with AES-256-GCM and associated data.

```text
KMS key
   |
   v
wrapped survey branch key in Core
   |
   +--> plaintext survey key in bounded worker cache
              |
              v
wrapped session key in Response
   |
   +--> plaintext session key in bounded worker cache
              |
              v
      AES-GCM answer ciphertext
```

Plaintext survey and session keys can therefore exist in backend worker memory.
The caches reduce repeated database and KMS work but are not sources of truth;
the persisted wrapped keys are. Answer associated data binds ciphertext to its
crypto version, response envelope, and answer locator. Session-key wrapping is
bound to the project, survey, session, and session locator.

## Session and envelope lifecycle

Session start coordinates two databases without a distributed transaction:

1. access and the final project subject are resolved;
2. the core session, subject effects, recognition-token effects, and any
   single-use link consumption are prepared but not committed;
3. the service derives the session locator, loads the survey key, creates a
   session key, and commits the response envelope;
4. the core transaction is committed;
5. only then may the raw browser resume token and any new recognition token be
   returned.

```text
resolved access + subject
            |
            v
prepare Core session and side effects
            |
            v
commit Response envelope
            |
            v
commit Core transaction
            |
            v
return browser credentials
```

If response-envelope creation fails, the uncommitted core work is rolled back.
If the response envelope commits but the core commit fails, the service attempts
to delete the orphan envelope and does not return the resume token. A
reconciliation job covers the opposite durable inconsistency: an in-progress
core session with no response envelope is marked `abandoned`.

Later respondent commands hash the raw resume token, load the core session,
reject expired, abandoned, and normally completed sessions, reproduce the
session locator, and load the matching response envelope. Session context can
be cached, but the persistent session and envelope remain the durable records.

## Current-answer semantics

FlowForm stores one current encrypted row per answer locator. Saving the same
question again performs an upsert that replaces the previous ciphertext,
nonce, mutation identifier, and update time. There is no encrypted answer
revision history, revision counter, or latest-revision pointer.

Before writing, the backend checks that the question belongs to the session's
frozen survey version and validates a non-cleared value against that question's
schema. A cleared answer is represented as an encrypted cleared state rather
than deletion of the response row. Each encryption uses a fresh nonce, and the
response schema rejects nonce reuse within one envelope.

```text
question in frozen version
            |
      validate one answer
            |
       encrypt new state
            |
            v
upsert current row by answer locator
            |
       old ciphertext replaced
```

The response write is authoritative for answer persistence. The later core
`answer_saved` event is analytics metadata, not the answer record. Completion
is currently a core session state transition: answers are validated when saved,
but completion does not evaluate cross-question requirements or reconstruct and
validate the complete answer set.

## Authorized reads and deletion

Studio results routes require the relevant survey permission before calling the
results service. Result assembly starts with core subjects, sessions, frozen
questions, and answer slots. It derives response locators, fetches matching
ciphertext, and decrypts only when the request asks for answer values.

```text
survey permission + Core metadata
              |
       derive slot locators
              |
              v
      Response envelope + answers
              |
       optionally decrypt
              |
              v
      Studio result or export
```

Deleting one response session is deliberately response-first: the response
envelope and its cascading answer rows are committed as deleted before the core
session is deleted. This ordering prioritizes removal of answer material if the
second database operation fails.

## Implemented limits

The active implementation is narrower than several historical Session
Encryption proposals:

- answers are current values, not immutable revisions;
- completion does not validate a complete canonical answer set;
- reconciliation marks core sessions with missing envelopes as abandoned, but
  it is not a general repair system for every possible cross-store inconsistency;
- response-first deletion has no durable pending-deletion record or automatic
  retry workflow if core deletion fails afterward;
- plaintext keys and authorized plaintext answers exist in backend memory while
  being used.

Deployment credential separation, effective KMS/IAM policy, backups, rotation
operations, log and trace sanitization, cache eviction on every lifecycle
transition, and handling of plaintext after an authorized read still require
operational evidence beyond the service and schema implementation.

## Related documents

- [[data-index|Data knowledge]]
- [[respondent-access-and-continuity|Respondent access and continuity]]
- [[submissions|Submissions]]
- [[security-model|Security model]]
- [[trust-boundaries|Trust boundaries]]
