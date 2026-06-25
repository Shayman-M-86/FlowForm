"""Integration tests for admin decrypt paths.

Verifies:
- Admin detail returns decrypted latest answers mapped to question keys
- Admin history returns full revision history decrypted
- Envelope not found raises error
- Family reconstruction from survey definition
- Graceful fallback for unknown or non-canonical values
"""

from __future__ import annotations

import os
import uuid
from typing import TYPE_CHECKING
from unittest.mock import patch
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from app.crypto._internal.aad import build_aad
from app.crypto._internal.nonces import generate_nonce
from app.crypto._internal.payload import build_plaintext_payload
from app.crypto._internal.wrapping import encrypt_answer
from app.crypto.locators import derive_answer_locator, derive_session_locator
from app.crypto.models import (
    LinkageKey,
    PlaintextSessionKey,
    RevisionContext,
)
from app.crypto.session_key import SessionEnvelopeCryptoContext
from app.domain.errors import EnvelopeNotFoundError
from app.repositories.core.submission_sessions import create_session
from app.repositories.response import (
    response_answer_repo,
    response_answer_revision_repo,
    response_envelope_repo,
)
from app.schema.enums import SubmissionAnswerState
from app.services.admin_responses.service import AdminResponseService
from tests.integration.core.factories import (
    make_project,
    make_response_store,
    make_survey,
    make_survey_question,
    make_survey_version,
    make_user,
)

if TYPE_CHECKING:
    from tests.conftest import DbSessions

_LINKAGE_SECRET = b"\xcc" * 32
_FAKE_LINKAGE_KEY = LinkageKey(version=1, secret=_LINKAGE_SECRET, aws_version_id="test-version")

_ADMIN_MODULE = "app.services.admin_responses.service"


def _setup_core_fixtures(core_db: Session):
    user = make_user()
    core_db.add(user)
    core_db.flush()

    project = make_project(user_id=user.id)
    core_db.add(project)
    core_db.flush()

    store = make_response_store(project_id=project.id, user_id=user.id)
    core_db.add(store)
    core_db.flush()

    survey = make_survey(project_id=project.id, response_store_id=store.id, user_id=user.id)
    core_db.add(survey)
    core_db.flush()

    version = make_survey_version(survey_id=survey.id, user_id=user.id)
    core_db.add(version)
    core_db.flush()

    question = make_survey_question(survey_version_id=version.id, question_key="q1")
    core_db.add(question)
    core_db.flush()

    return project, survey, version, question


def _create_session_and_envelope(core_db: Session, response_db: Session, project, survey, version):
    raw_token = "test-token-" + uuid.uuid4().hex[:8]
    session = create_session(
        core_db,
        project_id=project.id,
        survey_id=survey.id,
        survey_version_id=version.id,
        response_store_id=survey.default_response_store_id,
        link_id=None,
        project_subject_id=None,
        raw_browser_session_token=raw_token,
        linkage_key_version=1,
    )

    loc = derive_session_locator(session.id, _FAKE_LINKAGE_KEY)
    session_locator = loc.session_locator
    plaintext_dek = PlaintextSessionKey(os.urandom(32))
    wrapped_session_dek = os.urandom(64)

    envelope = response_envelope_repo.create(
        response_db,
        session_locator=session_locator,
        linkage_key_version=1,
        wrapped_session_dek=wrapped_session_dek,
        crypto_version=1,
    )

    return session, envelope, plaintext_dek, session_locator


def _mock_crypto_context(session_locator, envelope, plaintext_dek):
    return patch(
        f"{_ADMIN_MODULE}.load_session_envelope_crypto_context",
        return_value=SessionEnvelopeCryptoContext(
            session_locator=session_locator,
            envelope=envelope,
            plaintext_key=plaintext_dek,
        ),
    )


def _save_encrypted_answer(
    response_db: Session,
    session,
    envelope,
    plaintext_dek: PlaintextSessionKey,
    question_node_id: UUID,
    answer_value=None,
    answer_state: SubmissionAnswerState = "answered",
):
    answer_locator = derive_answer_locator(session.id, question_node_id, _FAKE_LINKAGE_KEY)
    revision_id = uuid.uuid4()

    answer_row, _ = response_answer_repo.get_or_create(
        response_db,
        envelope_id=envelope.id,
        answer_locator=answer_locator,
        latest_revision_id=revision_id,
    )

    plaintext = build_plaintext_payload(
        question_node_id=question_node_id,
        answer_state=answer_state,
        answer_value=answer_value,
    )
    nonce = generate_nonce()
    revision_ctx = RevisionContext(
        dek=plaintext_dek,
        crypto_version=envelope.crypto_version,
        envelope_id=answer_row.envelope_id,
        answer_id=answer_row.id,
        answer_locator=answer_locator,
        revision_id=revision_id,
        revision_number=1,
    )
    aad = build_aad(revision_ctx)
    ciphertext = encrypt_answer(plaintext, plaintext_dek, nonce, aad)

    response_answer_revision_repo.create(
        response_db,
        answer_id=answer_row.id,
        envelope_id=envelope.id,
        revision_number=1,
        nonce=nonce,
        ciphertext=ciphertext,
        client_mutation_id=uuid.uuid4(),
        revision_id=revision_id,
    )

    return answer_row


def _add_second_revision(
    response_db: Session,
    session,
    envelope,
    answer_row,
    plaintext_dek: PlaintextSessionKey,
    question_node_id: UUID,
    answer_value=None,
):
    answer_locator = derive_answer_locator(session.id, question_node_id, _FAKE_LINKAGE_KEY)
    revision_id = uuid.uuid4()

    plaintext = build_plaintext_payload(
        question_node_id=question_node_id,
        answer_state="answered",
        answer_value=answer_value,
    )
    nonce = generate_nonce()
    revision_ctx = RevisionContext(
        dek=plaintext_dek,
        crypto_version=envelope.crypto_version,
        envelope_id=answer_row.envelope_id,
        answer_id=answer_row.id,
        answer_locator=answer_locator,
        revision_id=revision_id,
        revision_number=2,
    )
    aad = build_aad(revision_ctx)
    ciphertext = encrypt_answer(plaintext, plaintext_dek, nonce, aad)

    response_answer_revision_repo.create(
        response_db,
        answer_id=answer_row.id,
        envelope_id=envelope.id,
        revision_number=2,
        nonce=nonce,
        ciphertext=ciphertext,
        client_mutation_id=uuid.uuid4(),
        revision_id=revision_id,
    )

    response_answer_revision_repo.update_latest_pointer(response_db, answer_row.id, revision_id)


class TestAdminDecryptDetail:
    def test_admin_detail_returns_decrypted_answers(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, envelope, plaintext_dek, session_locator = _create_session_and_envelope(
            core_db, response_db, project, survey, version,
        )

        _save_encrypted_answer(
            response_db, session, envelope, plaintext_dek,
            question_node_id=question.id, answer_value="test answer",
        )

        with _mock_crypto_context(session_locator, envelope, plaintext_dek):
            service = AdminResponseService()
            result = service.get_session_detail(
                core_db, response_db, survey_id=session.survey_id, session_id=session.id,
            )

        assert result.session.id == session.id
        assert len(result.answers) == 1
        assert result.answers[0].question_node_id == question.id
        assert result.answers[0].question_key == "q1"
        assert result.answers[0].answer_value == "test answer"
        assert result.answers[0].answer_state == "answered"

    def test_admin_detail_no_envelope_raises(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, _ = _setup_core_fixtures(core_db)
        raw_token = "test-token-" + uuid.uuid4().hex[:8]
        assert survey.default_response_store_id is not None
        session = create_session(
            core_db,
            project_id=project.id,
            survey_id=survey.id,
            survey_version_id=version.id,
            response_store_id=survey.default_response_store_id,
            link_id=None,
            project_subject_id=None,
            raw_browser_session_token=raw_token,
            linkage_key_version=1,
        )

        with (
            patch(
                f"{_ADMIN_MODULE}.load_session_envelope_crypto_context",
                side_effect=EnvelopeNotFoundError(),
            ),
            pytest.raises(EnvelopeNotFoundError),
        ):
            service = AdminResponseService()
            service.get_session_detail(
                core_db, response_db, survey_id=session.survey_id, session_id=session.id,
            )


class TestAdminDecryptHistory:
    def test_admin_history_returns_all_revisions(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, envelope, plaintext_dek, session_locator = _create_session_and_envelope(
            core_db, response_db, project, survey, version,
        )

        answer_row = _save_encrypted_answer(
            response_db, session, envelope, plaintext_dek,
            question_node_id=question.id, answer_value="first answer",
        )

        _add_second_revision(
            response_db, session, envelope, answer_row, plaintext_dek,
            question_node_id=question.id, answer_value="second answer",
        )

        with _mock_crypto_context(session_locator, envelope, plaintext_dek):
            service = AdminResponseService()
            result = service.get_session_history(
                core_db, response_db, survey_id=session.survey_id, session_id=session.id,
            )

        assert len(result.revisions) == 2
        values = [a.answer_value for a in result.revisions]
        assert "first answer" in values
        assert "second answer" in values
        revisions = [a.revision_number for a in result.revisions]
        assert 1 in revisions
        assert 2 in revisions


class TestAdminDecryptFamilyReconstruction:
    def test_family_reconstructed_and_value_typed(self, db_sessions: DbSessions) -> None:
        from app.schema.api.submission_sessions.answer_payload import ChoiceAnswerValue

        core_db, response_db = db_sessions.core, db_sessions.response
        user = make_user()
        core_db.add(user)
        core_db.flush()
        project = make_project(user_id=user.id)
        core_db.add(project)
        core_db.flush()
        store = make_response_store(project_id=project.id, user_id=user.id)
        core_db.add(store)
        core_db.flush()
        survey = make_survey(project_id=project.id, response_store_id=store.id, user_id=user.id)
        core_db.add(survey)
        core_db.flush()
        version = make_survey_version(survey_id=survey.id, user_id=user.id)
        core_db.add(version)
        core_db.flush()
        question = make_survey_question(
            survey_version_id=version.id,
            question_key="q1",
            question_schema={"id": "q1", "family": "choice", "label": "Pick"},
        )
        core_db.add(question)
        core_db.flush()

        session, envelope, plaintext_dek, session_locator = _create_session_and_envelope(
            core_db, response_db, project, survey, version,
        )
        _save_encrypted_answer(
            response_db, session, envelope, plaintext_dek,
            question_node_id=question.id, answer_value={"selected": ["o1", "o2"]},
        )

        with _mock_crypto_context(session_locator, envelope, plaintext_dek):
            service = AdminResponseService()
            result = service.get_session_detail(
                core_db, response_db, survey_id=session.survey_id, session_id=session.id,
            )

        answer = result.answers[0]
        assert answer.answer_family == "choice"
        assert isinstance(answer.answer_value, ChoiceAnswerValue)
        assert answer.answer_value.selected == ["o1", "o2"]

    def test_unknown_question_node_falls_back(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, _ = _setup_core_fixtures(core_db)
        session, envelope, plaintext_dek, session_locator = _create_session_and_envelope(
            core_db, response_db, project, survey, version,
        )
        orphan_node_id = uuid.uuid4()
        _save_encrypted_answer(
            response_db, session, envelope, plaintext_dek,
            question_node_id=orphan_node_id, answer_value={"selected": ["o1"]},
        )

        with _mock_crypto_context(session_locator, envelope, plaintext_dek):
            service = AdminResponseService()
            result = service.get_session_detail(
                core_db, response_db, survey_id=session.survey_id, session_id=session.id,
            )

        answer = result.answers[0]
        assert answer.question_node_id == orphan_node_id
        assert answer.answer_family is None
        assert answer.answer_value == {"selected": ["o1"]}

    def test_non_canonical_value_falls_back_keeping_family(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        user = make_user()
        core_db.add(user)
        core_db.flush()
        project = make_project(user_id=user.id)
        core_db.add(project)
        core_db.flush()
        store = make_response_store(project_id=project.id, user_id=user.id)
        core_db.add(store)
        core_db.flush()
        survey = make_survey(project_id=project.id, response_store_id=store.id, user_id=user.id)
        core_db.add(survey)
        core_db.flush()
        version = make_survey_version(survey_id=survey.id, user_id=user.id)
        core_db.add(version)
        core_db.flush()
        question = make_survey_question(
            survey_version_id=version.id,
            question_key="q1",
            question_schema={"id": "q1", "family": "choice", "label": "Pick"},
        )
        core_db.add(question)
        core_db.flush()

        session, envelope, plaintext_dek, session_locator = _create_session_and_envelope(
            core_db, response_db, project, survey, version,
        )
        _save_encrypted_answer(
            response_db, session, envelope, plaintext_dek,
            question_node_id=question.id, answer_value={"garbage": True},
        )

        with _mock_crypto_context(session_locator, envelope, plaintext_dek):
            service = AdminResponseService()
            result = service.get_session_detail(
                core_db, response_db, survey_id=session.survey_id, session_id=session.id,
            )

        answer = result.answers[0]
        assert answer.answer_family == "choice"
        assert answer.answer_value == {"garbage": True}
