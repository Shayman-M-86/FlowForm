# Session & Response Storage

## The Two-Database Model

Submission data lives in two separate PostgreSQL databases that never share a
foreign key:

- **Core DB** holds identity and session metadata: who took the survey, which
  subject they resolved to, when the session started and ended.
- **Response DB** holds encrypted answer payloads. It has no knowledge of users,
  subjects, or project structure. Every lookup into the response DB is done via
  opaque cryptographic locators.

This split means the response DB cannot be joined to the core DB to reconstruct
"who said what" without the encryption keys. The two databases are decoupled by
design, not just by convention.

---

## Session Lifecycle

A `submission_session` row in the core DB anchors the entire session. It stores:

- A hashed browser session token (the raw token never persists).
- A `session_status` (`in_progress` / `completed` / `expired`).
- A `linkage_key_version` — the version of the linkage secret used to derive
  this session's cryptographic locators.
- Timestamps for start, last activity, and completion.

No answer data lives in this row. It is the identity anchor; the response DB is
the payload store.

---

## Locators: The Cryptographic Bridge

The two databases are connected only through locators — fixed-length HMAC
digests derived from core-DB identifiers using a linkage secret. There are two
kinds:

- **Session locator** — derived from the `submission_session.id`. Stored in
  `response_envelopes.session_locator` (32-byte BYTEA, unique). It is what lets
  the service find the right envelope without ever storing a raw session UUID in
  the response DB.
- **Answer locator** — derived from a stable question-slot identifier (the
  question node UUID). Stored as the primary key of `response_answers`. It is
  what lets the service look up or overwrite the current answer for a given
  question without knowing anything about the survey structure.

Locators are computed, never stored in the core DB. The linkage secret is
versioned so it can be rotated; `linkage_key_version` on both the session row
and the response envelope tracks which version was used.

---

## Response Envelopes

Each session has exactly one `response_envelope` row in the response DB. It
holds:

- The `session_locator` (the bridge from the core DB).
- A `wrapped_session_dek` — the session data encryption key, wrapped by the
  survey branch key (not stored here in plaintext).
- A `crypto_version` for future algorithm migration.

The envelope is the container. Answer rows hang off it by a foreign key on
`envelope_id`.

---

## Answer Storage

`response_answers` stores one row per question slot per session. Each row holds:

- The `answer_locator` (primary key — the cryptographic address for this
  question's answer).
- `envelope_id` — the parent envelope.
- `ciphertext` and `nonce` — the AES-GCM encrypted payload.
- `client_mutation_id` — for idempotent saves (the client retrying a save does
  not produce duplicate rows).

Saving an answer is an upsert keyed on `answer_locator`. There is no append-
only revision table in the current schema; the single row is overwritten. A
clearing write is a null-payload ciphertext rather than a deletion.

---

## Transactional Consistency

Session start creates the core DB row first. Only after that succeeds does the
service write the response envelope. Answer saves are writes to the response DB
alone. Completion updates `session_status` in the core DB.

If the response DB write fails after the core DB row is committed, the orphaned
envelope is a known failure mode — reconciliation rather than rollback is the
intended remedy.

---

## Loose Threads

**Response answer revisions are designed but not yet in the schema.** The spec
describes an immutable append-only `response_answer_revisions` table (one row
per save, with a canonical "latest" pointer). The current schema uses a
single-row upsert model. Migration to append-only revisions is a planned but
unimplemented step.

**Linkage key rotation is versioned but not yet exercised.** The schema supports
multiple linkage key versions and the cache layer stores keys by version number,
but no rotation workflow has been built.
