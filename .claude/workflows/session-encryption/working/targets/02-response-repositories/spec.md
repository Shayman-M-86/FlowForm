# Pass 02: Response Repositories

## Goal

Implement the three response-database repositories that all service-layer code
will use to read and write encrypted response data. No crypto logic lives here —
repositories only move rows.

## Files to create

- `backend/app/repositories/response/response_envelope_repo.py`
- `backend/app/repositories/response/response_answer_repo.py`
- `backend/app/repositories/response/response_answer_revision_repo.py`
- `backend/app/repositories/response/__init__.py`

## Existing ORM models to use (read-only)

- `backend/app/schema/orm/response/response_envelope.py`
- `backend/app/schema/orm/response/response_answer.py`
- `backend/app/schema/orm/response/response_answer_revision.py`

## In scope

### ResponseEnvelopeRepo
- `create(session_locator: bytes, linkage_key_version: int, wrapped_dek: bytes, kms_key_ref: str, kms_context_version: int, crypto_version: int) -> ResponseEnvelope`
- `get_by_locator(session_locator: bytes) -> ResponseEnvelope | None`

### ResponseAnswerRepo
- `get_or_create(envelope_id: uuid.UUID, answer_locator: bytes) -> tuple[ResponseAnswer, bool]` — bool is True if created; handles simultaneous first-save via unique constraint retry
- `get_by_locator(envelope_id: uuid.UUID, answer_locator: bytes) -> ResponseAnswer | None`
- `lock_for_update(answer_id: uuid.UUID) -> ResponseAnswer | None` — SELECT FOR UPDATE

### ResponseAnswerRevisionRepo
- `get_by_mutation_id(answer_id: uuid.UUID, client_mutation_id: uuid.UUID) -> ResponseAnswerRevision | None`
- `create(answer_id: uuid.UUID, envelope_id: uuid.UUID, revision_number: int, nonce: bytes, ciphertext: bytes, client_mutation_id: uuid.UUID) -> ResponseAnswerRevision`
- `get_latest(answer_id: uuid.UUID) -> ResponseAnswerRevision | None`
- `get_history(answer_id: uuid.UUID) -> list[ResponseAnswerRevision]`
- `update_latest_pointer(answer_id: uuid.UUID, revision_id: uuid.UUID) -> None`

## Decisions locked by source docs

- Repositories touch only the response database — never the core database (doc 01, doc 02)
- No plaintext question IDs, user IDs, project IDs, survey IDs stored in response DB (doc 02)
- `get_or_create` must handle the unique answer_locator constraint race; use INSERT ... ON CONFLICT or catch IntegrityError and re-fetch (doc 04)

## Out of scope

- Crypto operations — pass 01 owns those
- KMS or Secrets Manager calls — pass 03
- Service-layer orchestration — passes 04 and 05
- Core database access

## Done when

- [ ] All three repo classes implemented with full type hints, mypy clean
- [ ] Integration tests cover: envelope create and fetch, answer get_or_create idempotency, revision create and latest pointer update, mutation ID dedup fetch
- [ ] Tests pass: `bash backend/scripts/run-tests.sh --ai -k "response_repo"`

## Dependencies

Pass 01 (crypto helpers) must be complete — repos import locator types.
