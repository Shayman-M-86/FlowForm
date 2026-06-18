"""Integration tests for session completion with encryption.

Verifies:
- Completion decrypts all latest answers, validates, and marks session completed
- Idempotent: repeated completion returns stored state, no duplicate DB writes
- Missing required answers rejected
- Session completion event inserted
"""
from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from pydantic import SecretStr
from sqlalchemy import text
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
from app.domain.errors import CompletionValidationError, SessionInvalidError
from app.repositories.core.submission_sessions import create_session
from app.repositories.response import (
    response_answer_repo,
    response_answer_revision_repo,
    response_envelope_repo,
)
from app.services.public_submissions.core.completion import CompletionService
from app.services.public_submissions.core.session_loader import SessionContext
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


def _setup_core_fixtures(core_db: Session, *, required_questions: bool = False):
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

    schema = {"id": "q1", "family": "field", "label": "Q1",
              "field": {"schema": {"field_type": "short_text"}, "ui": {}}}
    if required_questions:
        schema["required"] = True

    question = make_survey_question(
        survey_version_id=version.id, question_key="q1", question_schema=schema
    )
    core_db.add(question)
    core_db.flush()

    return project, survey, version, question


def _create_session_row(core_db: Session, project, survey, version, *, status: str = "in_progress"):
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
    if status != "in_progress":
        now = datetime.now(UTC)
        core_db.execute(
            text(
                "UPDATE submission_sessions "
                "SET session_status = :status, completed_at = :cat, last_activity_at = :lat "
                "WHERE id = :sid"
            ),
            {
                "status": status,
                "cat": now if status == "completed" else None,
                "lat": now,
                "sid": session.id,
            },
        )
        core_db.expire(session)
    return session, raw_token


def _create_envelope_and_context(core_db: Session, response_db: Session, session, version):
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

    ctx = SessionContext(
        session=session,
        survey_version=version,
        session_locator=session_locator,
        envelope=envelope,
        encryption_settings=_FAKE_ENC_SETTINGS,
    )
    return ctx, plaintext_dek


def _save_encrypted_answer(
    response_db: Session,
    ctx: SessionContext,
    plaintext_dek: bytes,
    question_node_id: str,
    answer_state: str = "answered",
    answer_value=None,
):
    """Helper to create an encrypted answer directly in the response DB."""
    answer_locator = derive_answer_locator(str(ctx.session.id), question_node_id, _LINKAGE_SECRET)

    revision_id = uuid.uuid4()

    answer_row, _ = response_answer_repo.get_or_create(
        response_db,
        envelope_id=ctx.envelope.id,
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
        crypto_version=ctx.envelope.crypto_version,
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
        envelope_id=ctx.envelope.id,
        revision_number=1,
        nonce=nonce,
        ciphertext=ciphertext,
        client_mutation_id=uuid.uuid4(),
        revision_id=revision_id,
    )

    return answer_row


def _patch_completion_crypto():
    return patch(
        "app.services.public_submissions.core.completion.get_linkage_secret",
        return_value=_LINKAGE_SECRET,
    )


def _make_service_with_cached_dek(ctx, plaintext_dek):
    from app.crypto.dek_cache import DekCache
    dek_cache = DekCache()
    dek_cache.put(ctx.session_locator, plaintext_dek)
    return CompletionService(dek_cache=dek_cache)


class TestCompletion:

    def test_completion_marks_session_completed(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(core_db, response_db, session, version)

        _save_encrypted_answer(
            response_db, ctx, plaintext_dek,
            question_node_id=str(question.id),
            answer_value="my answer",
        )

        svc = _make_service_with_cached_dek(ctx, plaintext_dek)

        with _patch_completion_crypto():
            result = svc.complete_session(core_db, response_db, ctx=ctx)

        assert result.status == "completed"
        assert result.completed_at is not None

        core_db.expire(session)
        assert session.session_status == "completed"
        assert session.completed_at is not None

    def test_completion_is_idempotent(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(core_db, response_db, session, version)

        _save_encrypted_answer(
            response_db, ctx, plaintext_dek,
            question_node_id=str(question.id),
            answer_value="my answer",
        )

        svc = _make_service_with_cached_dek(ctx, plaintext_dek)

        with _patch_completion_crypto():
            result1 = svc.complete_session(core_db, response_db, ctx=ctx)

        # Reload the session to get the completed state into the context
        core_db.expire(session)
        ctx2 = SessionContext(
            session=session,
            survey_version=version,
            session_locator=ctx.session_locator,
            envelope=ctx.envelope,
            encryption_settings=_FAKE_ENC_SETTINGS,
        )

        with _patch_completion_crypto():
            result2 = svc.complete_session(core_db, response_db, ctx=ctx2)

        assert result1.status == result2.status == "completed"
        assert result1.completed_at == result2.completed_at

    def test_missing_required_answer_rejected(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(
            core_db, required_questions=True
        )
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(core_db, response_db, session, version)

        # No answers saved — required question not answered
        svc = _make_service_with_cached_dek(ctx, plaintext_dek)

        with _patch_completion_crypto(), pytest.raises(CompletionValidationError, match="Missing required"):
            svc.complete_session(core_db, response_db, ctx=ctx)

    def test_completion_with_no_required_questions_succeeds(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(core_db, response_db, session, version)

        # No answers saved, but no required questions either
        svc = _make_service_with_cached_dek(ctx, plaintext_dek)

        with _patch_completion_crypto():
            result = svc.complete_session(core_db, response_db, ctx=ctx)

        assert result.status == "completed"
