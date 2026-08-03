# Answer Storage

## Purpose

This document explains how answers are represented once a session has a response envelope.

## Model

The response side has two tables — see `07-storage-and-flows-reference.md`
Section 3 for exact columns and constraints.

`response_envelopes` holds one encrypted response container for one submission session.

`response_answers` holds **one current row per answer locator**, primary
keyed on `answer_locator`. There is no separate revision-history table.

## Current answer, not revision history

Each answer save overwrites the stored row for its answer locator via
`upsert_current()` (`backend/app/repositories/response/response_answer_repo.py`,
an `INSERT ... ON CONFLICT (answer_locator) DO UPDATE`). Old ciphertext is
not retained — the database only ever holds the most recent encrypted
value for a question within a session.

There is no revision number, no "latest pointer" column, and no history
table to page through. Anything needing prior answer states (e.g. audit or
compliance requirements) would need a new capability — it does not exist
today.

## Clearing an answer

Clearing an answer is not deletion of the row.

A clear operation encrypts a payload with a cleared state and a null answer
value, then upserts it into the same `response_answers` row — overwriting
whatever was there before, the same as any other answer change.

## Save (first or changed answer)

There is a single write path, not separate first-save/changed-answer cases:

- derive the answer locator from `(session_id, question_node_id,
  linkage_key_version)`;
- encrypt the answer payload with a fresh nonce;
- upsert the row for that answer locator — inserts if it does not exist
  yet, otherwise overwrites `ciphertext`, `nonce`, `client_mutation_id`,
  and `updated_at`.

Simultaneous first saves for the same answer locator are handled by the
`ON CONFLICT` clause itself — the database resolves the race, not
application-level locking.

## Idempotency

Each answer mutation may carry a client mutation ID (`client_mutation_id`
is nullable on `response_answers`).

If the stored row already has the same client mutation ID as the incoming
request, the save should return the existing stored row rather than
re-encrypting and writing again — see `03-session-envelope-lifecycle.md`
Section 3, steps 2-3.

This protects against network retries, browser retries, and lost HTTP
responses.

## Concurrency

The `answer_locator` primary key and `ON CONFLICT DO UPDATE` are the
concurrency boundary — there is no separate revision-number counter to
lock around. Two concurrent saves for the same answer locator race on the
upsert itself; the last write wins, consistent with there being no
revision history to preserve.

`uq_response_answers_envelope_id_nonce` still guards against nonce reuse
within an envelope across separate writes (AES-GCM safety) — see
`05-crypto-key-model.md`.

## Validation rule

The backend must validate answers against the frozen survey version before saving.

Frontend validation is useful for UX but not trusted for persistence.
