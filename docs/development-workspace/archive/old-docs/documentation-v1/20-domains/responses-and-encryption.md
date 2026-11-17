---
title: Responses and encryption
aliases:
  - "Responses and encryption"
document_type: domain
status: draft
authority: canonical
verified_against_commit: ad26b87e9820
tags: [security]
related_code:
  - "../../backend/app/crypto/"
  - "../../backend/app/schema/orm/response/"
  - "../../backend/app/services/public_submissions/core/actions/"
  - "../../backend/app/services/admin_results/"
  - "../../backend/app/db/manager.py"
  - "../../infra/database/init/schema/flowform_response_db_schema_v4.sql"
related_docs:
  - "Submissions"
  - "Security model"
  - "Data flows"
  - "Backend implementation"
---

# Responses and encryption

Defines the storage and cryptographic boundary that keeps answer content out of
identity-bearing core data. It documents data minimisation at rest, not
protection from a fully compromised backend, which can access both databases and
the required keys.

## Purpose

FlowForm stores identifying, survey, and submission metadata in the core
database while storing encrypted current answers in a separately mapped response
database. Application-derived opaque locators connect the two sides without
placing core identifiers in response rows.

## Responsibilities

- Maintain distinct SQLAlchemy bases and independently configurable engines,
  sessions, schemas, and runtime credentials for core and response persistence.
- Derive 32-byte session and answer locators with HMAC-SHA256 and a versioned
  linkage secret held in AWS Secrets Manager.
- Create one random survey branch key per survey, wrapped by AWS KMS with a
  project/survey encryption context.
- Create one random session data-encryption key, wrap it under the survey key,
  and store only the wrapped form in the response envelope.
- Encrypt answer payloads with AES-256-GCM, a fresh 12-byte nonce, and
  context-derived additional authenticated data.
- Decrypt results in the backend for authorized reads and delete response data
  before the corresponding core session during individual-session deletion.
- Cache plaintext linkage, survey, and session key material in-process for
  bounded periods to avoid repeated external calls and unwrap operations.

## Non-responsibilities

- The response database does not own users, emails, project membership,
  subjects, participants, surveys, question identifiers, or session lifecycle.
- Encryption does not decide which respondent may start a session or which
  Studio user may view results.
- The database split does not protect answer plaintext from the backend process
  during validation, encryption, decryption, or key caching.
- This domain does not prove deployment credential separation, KMS policy,
  backup handling, or live key rotation beyond the checked-in application code.

## Main entities and invariants

| Entity | Store | Important invariant |
| --- | --- | --- |
| Survey encryption key | Core | One KMS-wrapped branch key per survey, bound to project/survey context. |
| Linkage-key version | Core plus Secrets Manager | Maps an application version to one AWS secret version so historical locators remain derivable. |
| Submission answer slot | Core | Holds session/question linkage and the UUID used as locator input, never the answer value. |
| Response envelope | Response | Unique opaque session locator, linkage-key version, wrapped session key, and crypto version only. |
| Response answer | Response | Opaque answer locator, envelope UUID, ciphertext, nonce, optional mutation ID, and timestamp only. |

The response schema has no `user_id`, email, project ID, survey ID, subject ID,
session ID, question ID, or foreign key to core data. Nonce length and ciphertext
presence are constrained, and `(envelope_id, nonce)` is unique to guard against
AES-GCM nonce reuse under one session key.

## Important workflows

1. Publishing a survey ensures a 32-byte branch key exists, wraps it with KMS,
   and persists the ciphertext and encryption-context version in core data.
2. Session start obtains the current linkage key, derives the session locator,
   creates a random session key, wraps it under the survey key, and commits a
   response envelope before core session commit.
3. Answer save creates or finds the core slot, derives its answer locator,
   serializes question ID/state/value inside the plaintext payload, encrypts it,
   and upserts the current response row.
4. Results reads start from authorized core sessions/slots, re-derive locators,
   load and unwrap the session key, fetch response rows, verify AES-GCM AAD, and
   return structured decrypted values when requested.
5. Individual-session deletion derives the envelope locator, commits response
   deletion (cascading its answers), then commits deletion of the core session.

## Implementation map

- `backend/app/crypto/locators.py`, `survey_key.py`, `session_key.py`, and
  `answers.py` expose application-aware locator and encryption operations.
- `backend/app/crypto/_internal/` owns AES-GCM wrapping, nonces, AAD, KMS
  context, payload serialization, and linkage-secret retrieval.
- `backend/app/schema/orm/response/` and the response SQL schema define the only
  response-side rows.
- `backend/app/db/manager.py` constructs independent core and response engines
  and request sessions.
- `backend/app/services/public_submissions/core/actions/` writes envelopes and
  answers; `backend/app/services/admin_results/` reads, decrypts, exports, and
  deletes them.
- Integration tests verify ORM routing, opaque locator shape, encrypted session
  start, answer round trips, and response-first deletion ordering.

## Verified gaps and open questions

- Cross-database operations are sagas, not atomic transactions. Compensation
  and reconciliation cover only some partial-commit directions.
- Individual-session deletion commits response deletion before core deletion; a
  later core failure leaves metadata whose retry can fail because the envelope
  is already absent.
- Project and survey deletion cascade through core data without an observed
  response-store sweep, so anonymous ciphertext can remain after its core
  linkage and wrapped survey key are deleted.
- `external_postgres` is accepted as response-store metadata, but request code
  uses one configured response session; dynamic external-store routing was not
  found.
- Plaintext keys and full session crypto contexts are cached in worker memory.
  Rotation, cache eviction on all terminal paths, and memory-exposure policy need
  stronger operational and test coverage.
- Database configuration does not validate that core and response URLs, database
  names, or users are distinct. Deployment must preserve that boundary.

## Related documents

- [[submissions|Submissions]]
- [[security-model|Security model]]
- [[data-flows|Data flows]]
- [[backend|Backend implementation]]
