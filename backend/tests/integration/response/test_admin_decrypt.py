"""Integration tests for admin decrypt paths.

Verifies:
- Admin detail returns decrypted latest answers mapped to question keys
- Admin history returns full revision history decrypted
- Envelope not found raises error
"""
from __future__ import annotations

import os
import uuid
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.core.config import EncryptionSettings
from app.crypto import (
    build_aad,
    build_plaintext_payload,
    derive_answer_locator,
    derive_session_locator,
    encrypt_answer,
    generate_nonce,
)
from app.domain.errors import EnvelopeNotFoundError
from app.repositories.core.submission_sessions import create_session
from app.repositories.response import (
    response_answer_repo,
    response_answer_revision_repo,
    response_envelope_repo,
)
from app.services.public_submissions.core.admin_decrypt import (
    decrypt_session_detail,
    decrypt_session_history,
)
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
_FAKE_ENC_SETTINGS = EncryptionSettings(
    kms_key_arn="arn:aws:kms:us-east-1:000000000000:key/test-key",
    linkage_secret_arn="arn:aws:secretsmanager:us-east-1:000000000000:secret:test",
    aws_region="us-east-1",
    aws_access_key_id=SecretStr("AKIAIOSFODNN7EXAMPLE"),
    aws_secret_access_key=SecretStr("wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"),
)
_PAYLOAD_VERSION = 1


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

    survey = make_survey(
        project_id=project.id, response_store_id=store.id, user_id=user.id
    )
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
    )

    session_locator = derive_session_locator(str(session.id), _LINKAGE_SECRET)
    plaintext_dek = os.urandom(32)
    wrapped_dek = os.urandom(64)

    envelope = response_envelope_repo.create(
        response_db,
        session_locator=session_locator,
        linkage_key_version=1,
        wrapped_dek=wrapped_dek,
        kms_key_arn="arn:aws:kms:us-east-1:000000000000:key/test-key",
        kms_context_version=1,
        crypto_version=1,
    )

    return session, envelope, plaintext_dek


def _save_encrypted_answer(
    response_db: Session,
    session,
    envelope,
    plaintext_dek: bytes,
    question_node_id: str,
    answer_value=None,
    answer_state: str = "answered",
):
    answer_locator = derive_answer_locator(str(session.id), question_node_id, _LINKAGE_SECRET)
    revision_id = uuid.uuid4()

    answer_row, _ = response_answer_repo.get_or_create(
        response_db,
        envelope_id=envelope.id,
        answer_locator=answer_locator,
        latest_revision_id=revision_id,
    )

    plaintext = build_plaintext_payload(
        payload_version=_PAYLOAD_VERSION,
        question_node_id=question_node_id,
        answer_state=answer_state,
        answer_value=answer_value,
    )
    nonce = generate_nonce()
    aad = build_aad(
        crypto_version=envelope.crypto_version,
        envelope_id=answer_row.envelope_id,
        answer_id=answer_row.id,
        answer_locator=answer_locator,
        revision_id=revision_id,
        revision_number=1,
    )
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
    plaintext_dek: bytes,
    question_node_id: str,
    answer_value=None,
):
    answer_locator = derive_answer_locator(str(session.id), question_node_id, _LINKAGE_SECRET)
    revision_id = uuid.uuid4()

    plaintext = build_plaintext_payload(
        payload_version=_PAYLOAD_VERSION,
        question_node_id=question_node_id,
        answer_state="answered",
        answer_value=answer_value,
    )
    nonce = generate_nonce()
    aad = build_aad(
        crypto_version=envelope.crypto_version,
        envelope_id=answer_row.envelope_id,
        answer_id=answer_row.id,
        answer_locator=answer_locator,
        revision_id=revision_id,
        revision_number=2,
    )
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


def _patch_admin_crypto():
    return (
        patch(
            "app.services.public_submissions.core.admin_decrypt.get_linkage_secret",
            return_value=_LINKAGE_SECRET,
        ),
        patch(
            "app.services.public_submissions.core.admin_decrypt.unwrap_dek",
        ),
    )


class TestAdminDecryptDetail:

    def test_admin_detail_returns_decrypted_answers(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, envelope, plaintext_dek = _create_session_and_envelope(
            core_db, response_db, project, survey, version
        )

        _save_encrypted_answer(
            response_db, session, envelope, plaintext_dek,
            question_node_id=str(question.id),
            answer_value="test answer",
        )

        p1, p2 = _patch_admin_crypto()
        with p1, p2 as mock_unwrap:
            mock_unwrap.return_value = plaintext_dek
            result = decrypt_session_detail(
                core_db, response_db,
                session=session,
                encryption_settings=_FAKE_ENC_SETTINGS,
            )

        assert result.session_id == str(session.id)
        assert len(result.answers) == 1
        assert result.answers[0].question_node_id == str(question.id)
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
        )

        p1, _ = _patch_admin_crypto()
        with p1, pytest.raises(EnvelopeNotFoundError):
            decrypt_session_detail(
                core_db, response_db,
                session=session,
                encryption_settings=_FAKE_ENC_SETTINGS,
            )


class TestAdminDecryptHistory:

    def test_admin_history_returns_all_revisions(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, envelope, plaintext_dek = _create_session_and_envelope(
            core_db, response_db, project, survey, version
        )

        answer_row = _save_encrypted_answer(
            response_db, session, envelope, plaintext_dek,
            question_node_id=str(question.id),
            answer_value="first answer",
        )

        _add_second_revision(
            response_db, session, envelope, answer_row, plaintext_dek,
            question_node_id=str(question.id),
            answer_value="second answer",
        )

        p1, p2 = _patch_admin_crypto()
        with p1, p2 as mock_unwrap:
            mock_unwrap.return_value = plaintext_dek
            result = decrypt_session_history(
                core_db, response_db,
                session=session,
                encryption_settings=_FAKE_ENC_SETTINGS,
            )

        assert len(result.answers) == 2
        values = [a.answer_value for a in result.answers]
        assert "first answer" in values
        assert "second answer" in values
        revisions = [a.revision_number for a in result.answers]
        assert 1 in revisions
        assert 2 in revisions
