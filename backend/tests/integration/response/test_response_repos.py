from __future__ import annotations

import os
import uuid
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.repositories.response import (
    response_answer_repo,
    response_answer_revision_repo,
    response_envelope_repo,
)

if TYPE_CHECKING:
    from app.schema.orm.response.response_envelope import ResponseEnvelope


def _locator(seed: int = 0) -> bytes:
    return (seed).to_bytes(1, "big") * 32


def _nonce(seed: int = 0) -> bytes:
    return (seed).to_bytes(1, "big") * 12


def _ciphertext(seed: int = 0) -> bytes:
    return os.urandom(48)


def _wrapped_dek() -> bytes:
    return os.urandom(64)


def _create_envelope(db: Session, seed: int = 0) -> ResponseEnvelope:
    return response_envelope_repo.create(
        db,
        session_locator=_locator(seed),
        linkage_key_version=1,
        wrapped_dek=_wrapped_dek(),
        kms_key_arn="arn:aws:kms:us-east-1:000000000000:key/test-key",
        kms_context_version=1,
        crypto_version=1,
    )


# ── ResponseEnvelopeRepo ──


class TestResponseEnvelopeRepo:
    def test_create_and_get_by_locator(self, response_db_session: Session) -> None:
        locator = _locator(1)
        envelope = response_envelope_repo.create(
            response_db_session,
            session_locator=locator,
            linkage_key_version=1,
            wrapped_dek=_wrapped_dek(),
            kms_key_arn="arn:aws:kms:us-east-1:000000000000:key/test-key",
            kms_context_version=1,
            crypto_version=1,
        )
        assert envelope.id is not None
        assert envelope.session_locator == locator

        fetched = response_envelope_repo.get_by_locator(response_db_session, locator)
        assert fetched is not None
        assert fetched.id == envelope.id

    def test_get_by_locator_returns_none_for_missing(self, response_db_session: Session) -> None:
        result = response_envelope_repo.get_by_locator(response_db_session, _locator(99))
        assert result is None


# ── ResponseAnswerRepo ──


class TestResponseAnswerRepo:
    def test_get_or_create_creates_new(self, response_db_session: Session) -> None:
        envelope = _create_envelope(response_db_session, seed=10)
        rev_id = uuid.uuid4()
        answer_locator = _locator(20)

        answer, created = response_answer_repo.get_or_create(
            response_db_session,
            envelope_id=envelope.id,
            answer_locator=answer_locator,
            latest_revision_id=rev_id,
        )
        assert created is True
        assert answer.envelope_id == envelope.id
        assert answer.answer_locator == answer_locator

    def test_get_or_create_returns_existing_on_duplicate(self, response_db_session: Session) -> None:
        envelope = _create_envelope(response_db_session, seed=11)
        rev_id_1 = uuid.uuid4()
        rev_id_2 = uuid.uuid4()
        answer_locator = _locator(21)

        answer1, created1 = response_answer_repo.get_or_create(
            response_db_session,
            envelope_id=envelope.id,
            answer_locator=answer_locator,
            latest_revision_id=rev_id_1,
        )
        assert created1 is True

        answer2, created2 = response_answer_repo.get_or_create(
            response_db_session,
            envelope_id=envelope.id,
            answer_locator=answer_locator,
            latest_revision_id=rev_id_2,
        )
        assert created2 is False
        assert answer2.id == answer1.id

    def test_get_by_locator(self, response_db_session: Session) -> None:
        envelope = _create_envelope(response_db_session, seed=12)
        answer_locator = _locator(22)
        rev_id = uuid.uuid4()

        response_answer_repo.get_or_create(
            response_db_session,
            envelope_id=envelope.id,
            answer_locator=answer_locator,
            latest_revision_id=rev_id,
        )

        found = response_answer_repo.get_by_locator(
            response_db_session, envelope.id, answer_locator
        )
        assert found is not None
        assert found.answer_locator == answer_locator

    def test_get_by_locator_returns_none(self, response_db_session: Session) -> None:
        envelope = _create_envelope(response_db_session, seed=13)
        result = response_answer_repo.get_by_locator(
            response_db_session, envelope.id, _locator(99)
        )
        assert result is None

    def test_lock_for_update(self, response_db_session: Session) -> None:
        envelope = _create_envelope(response_db_session, seed=14)
        rev_id = uuid.uuid4()

        answer, _ = response_answer_repo.get_or_create(
            response_db_session,
            envelope_id=envelope.id,
            answer_locator=_locator(24),
            latest_revision_id=rev_id,
        )

        locked = response_answer_repo.lock_for_update(response_db_session, answer.id)
        assert locked is not None
        assert locked.id == answer.id


# ── ResponseAnswerRevisionRepo ──


class TestResponseAnswerRevisionRepo:
    def _setup_answer(
        self, db: Session, envelope_seed: int, locator_seed: int
    ) -> tuple:
        """Create envelope + answer, return (envelope, answer)."""
        envelope = _create_envelope(db, seed=envelope_seed)
        rev_placeholder = uuid.uuid4()
        answer, _ = response_answer_repo.get_or_create(
            db,
            envelope_id=envelope.id,
            answer_locator=_locator(locator_seed),
            latest_revision_id=rev_placeholder,
        )
        return envelope, answer

    def test_create_revision(self, response_db_session: Session) -> None:
        envelope, answer = self._setup_answer(response_db_session, 30, 40)
        mutation_id = uuid.uuid4()

        revision = response_answer_revision_repo.create(
            response_db_session,
            answer_id=answer.id,
            envelope_id=envelope.id,
            revision_number=1,
            nonce=_nonce(1),
            ciphertext=_ciphertext(),
            client_mutation_id=mutation_id,
        )
        assert revision.id is not None
        assert revision.revision_number == 1
        assert revision.answer_id == answer.id

    def test_get_by_mutation_id(self, response_db_session: Session) -> None:
        envelope, answer = self._setup_answer(response_db_session, 31, 41)
        mutation_id = uuid.uuid4()

        response_answer_revision_repo.create(
            response_db_session,
            answer_id=answer.id,
            envelope_id=envelope.id,
            revision_number=1,
            nonce=_nonce(2),
            ciphertext=_ciphertext(),
            client_mutation_id=mutation_id,
        )

        found = response_answer_revision_repo.get_by_mutation_id(
            response_db_session, answer.id, mutation_id
        )
        assert found is not None
        assert found.client_mutation_id == mutation_id

    def test_get_by_mutation_id_returns_none(self, response_db_session: Session) -> None:
        _, answer = self._setup_answer(response_db_session, 32, 42)
        result = response_answer_revision_repo.get_by_mutation_id(
            response_db_session, answer.id, uuid.uuid4()
        )
        assert result is None

    def test_update_latest_pointer_and_get_latest(self, response_db_session: Session) -> None:
        envelope, answer = self._setup_answer(response_db_session, 33, 43)

        rev1 = response_answer_revision_repo.create(
            response_db_session,
            answer_id=answer.id,
            envelope_id=envelope.id,
            revision_number=1,
            nonce=_nonce(3),
            ciphertext=_ciphertext(),
            client_mutation_id=uuid.uuid4(),
        )

        response_answer_revision_repo.update_latest_pointer(
            response_db_session, answer.id, rev1.id
        )

        latest = response_answer_revision_repo.get_latest(response_db_session, answer.id)
        assert latest is not None
        assert latest.id == rev1.id

    def test_get_history(self, response_db_session: Session) -> None:
        envelope, answer = self._setup_answer(response_db_session, 34, 44)

        rev1 = response_answer_revision_repo.create(
            response_db_session,
            answer_id=answer.id,
            envelope_id=envelope.id,
            revision_number=1,
            nonce=_nonce(4),
            ciphertext=_ciphertext(),
            client_mutation_id=uuid.uuid4(),
        )
        response_answer_revision_repo.update_latest_pointer(
            response_db_session, answer.id, rev1.id
        )

        rev2 = response_answer_revision_repo.create(
            response_db_session,
            answer_id=answer.id,
            envelope_id=envelope.id,
            revision_number=2,
            nonce=_nonce(5),
            ciphertext=_ciphertext(),
            client_mutation_id=uuid.uuid4(),
        )
        response_answer_revision_repo.update_latest_pointer(
            response_db_session, answer.id, rev2.id
        )

        history = response_answer_revision_repo.get_history(response_db_session, answer.id)
        assert len(history) == 2
        assert history[0].revision_number == 1
        assert history[1].revision_number == 2

    def test_get_latest_returns_none_for_missing_answer(self, response_db_session: Session) -> None:
        result = response_answer_revision_repo.get_latest(response_db_session, uuid.uuid4())
        assert result is None
