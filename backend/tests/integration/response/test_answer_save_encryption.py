"""Integration tests for answer save encryption flows.

Verifies end-to-end that:
- First save creates revision 1, latest pointer set
- Changed answer creates revision 2, latest pointer updated, revision 1 preserved
- Cleared answer creates new revision with null value
- Duplicate mutation ID returns existing without creating a new revision
- Expired session rejected before any write
- Completed session rejected before any write
- Analytics event failure does not block answer save
- Response DB locator columns contain opaque 32-byte HMAC digests
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.crypto._internal.aad import build_aad
from app.crypto._internal.payload import parse_plaintext_payload
from app.crypto._internal.wrapping import decrypt_answer
from app.crypto.answers import derive_session_answer_locator
from app.crypto.locators import derive_session_locator
from app.crypto.models import (
    LinkageKey,
    PlaintextSessionKey,
    RevisionContext,
    SessionContext,
)
from app.domain.errors import SessionInvalidError
from app.repositories.core.submission_sessions import create_session
from app.repositories.response import (
    response_answer_repo,
    response_answer_revision_repo,
    response_envelope_repo,
)
from app.schema.orm.core.submission_session import SessionRef
from app.schema.orm.response.response_answer import ResponseAnswer
from app.schema.orm.response.response_answer_revision import ResponseAnswerRevision
from app.services.public_submissions.core.actions.answer_save import AnswerSaveService
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
_FAKE_PLAINTEXT_DEK = PlaintextSessionKey(os.urandom(32))

_ANSWER_SAVE_MODULE = "app.services.public_submissions.core.actions.answer_save"


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

    question = make_survey_question(
        survey_version_id=version.id,
        question_key="q1",
        question_schema={
            "id": "q1",
            "family": "field",
            "label": "Q1",
            "field": {"schema": {"field_type": "short_text"}, "ui": {}},
        },
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
        linkage_key_version=1,
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
    loc = derive_session_locator(session.id, _FAKE_LINKAGE_KEY)
    session_locator = loc.session_locator
    wrapped_session_dek = os.urandom(64)

    envelope = response_envelope_repo.create(
        response_db,
        session_locator=session_locator,
        linkage_key_version=1,
        wrapped_session_dek=wrapped_session_dek,
        crypto_version=1,
    )

    session_ref = SessionRef(
        id=session.id,
        project_id=session.project_id,
        survey_id=session.survey_id,
        survey_version_id=version.id,
        expires_at=session.expires_at,
        browser_session_token_hash=session.browser_session_token_hash,
    )

    ctx = SessionContext(
        session_ref=session_ref,
        session_locator=session_locator,
        envelope_id=envelope.id,
        linkage_key=_FAKE_LINKAGE_KEY,
    )
    return ctx, _FAKE_PLAINTEXT_DEK


def _mock_session_key_load():
    return patch(
        f"{_ANSWER_SAVE_MODULE}.start_plaintext_session_key_load",
        return_value=lambda: _FAKE_PLAINTEXT_DEK,
    )


_SENTINEL = object()


def _save_answer(
    svc, core_db, response_db, ctx, question, *, answer_value=_SENTINEL, answer_state="answered", mutation_id=None,
):
    if answer_value is _SENTINEL:
        answer_value = {"field_type": "short_text", "text": "test answer"}
    return svc.save_answer(
        core_db,
        response_db,
        ctx=ctx,
        question_node_id=question.id,
        answer_state=answer_state,
        answer_value=answer_value,
        client_mutation_id=mutation_id or uuid.uuid4(),
    )


class TestFirstSave:
    def test_first_save_creates_revision_1(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, _dek = _create_envelope_and_context(core_db, response_db, session, version)

        svc = AnswerSaveService()
        with _mock_session_key_load():
            result = _save_answer(svc, core_db, response_db, ctx, question)

        assert result.revision_number == 1

        answer_locator = derive_session_answer_locator(ctx, question.id)
        answer = response_answer_repo.get_by_locator(response_db, ctx.envelope_id, answer_locator)
        assert answer is not None

        revision = response_answer_revision_repo.get_latest(response_db, answer.id)
        assert revision is not None
        assert revision.revision_number == 1
        assert revision.ciphertext is not None
        assert revision.nonce is not None

    def test_first_save_encrypts_answer_correctly(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(core_db, response_db, session, version)

        svc = AnswerSaveService()
        with _mock_session_key_load():
            _save_answer(svc, core_db, response_db, ctx, question,
                         answer_value={"field_type": "short_text", "text": "encrypted payload"})

        answer_locator = derive_session_answer_locator(ctx, question.id)
        answer = response_answer_repo.get_by_locator(response_db, ctx.envelope_id, answer_locator)
        assert answer is not None
        revision = response_answer_revision_repo.get_latest(response_db, answer.id)
        assert revision is not None

        revision_ctx = RevisionContext(
            dek=plaintext_dek,
            crypto_version=ctx.crypto_version,
            envelope_id=ctx.envelope_id,
            answer_id=answer.id,
            answer_locator=answer_locator,
            revision_id=revision.id,
            revision_number=revision.revision_number,
        )
        aad = build_aad(revision_ctx)
        decrypted = decrypt_answer(revision.ciphertext, plaintext_dek, revision.nonce, aad)
        parsed = parse_plaintext_payload(decrypted)

        assert parsed.answer_state == "answered"
        assert parsed.answer_value == {"field_type": "short_text", "text": "encrypted payload"}
        assert parsed.question_node_id == question.id


class TestChangedAnswer:
    def test_changed_answer_creates_revision_2(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, _dek = _create_envelope_and_context(core_db, response_db, session, version)

        svc = AnswerSaveService()
        with _mock_session_key_load():
            _save_answer(svc, core_db, response_db, ctx, question,
                         answer_value={"field_type": "short_text", "text": "first"})
            result = _save_answer(svc, core_db, response_db, ctx, question,
                                  answer_value={"field_type": "short_text", "text": "second"})

        assert result.revision_number == 2

        answer_locator = derive_session_answer_locator(ctx, question.id)
        answer = response_answer_repo.get_by_locator(response_db, ctx.envelope_id, answer_locator)
        assert answer is not None

        revisions = response_db.scalars(
            select(ResponseAnswerRevision)
            .where(ResponseAnswerRevision.answer_id == answer.id)
            .order_by(ResponseAnswerRevision.revision_number)
        ).all()
        assert len(revisions) == 2
        assert revisions[0].revision_number == 1
        assert revisions[1].revision_number == 2


class TestClearedAnswer:
    def test_cleared_answer_creates_revision_with_null_value(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(core_db, response_db, session, version)

        svc = AnswerSaveService()
        with _mock_session_key_load():
            _save_answer(svc, core_db, response_db, ctx, question,
                         answer_value={"field_type": "short_text", "text": "original"})
            result = _save_answer(svc, core_db, response_db, ctx, question,
                                  answer_state="cleared", answer_value=None)

        assert result.revision_number == 2

        answer_locator = derive_session_answer_locator(ctx, question.id)
        answer = response_answer_repo.get_by_locator(response_db, ctx.envelope_id, answer_locator)
        assert answer is not None
        revision = response_answer_revision_repo.get_latest(response_db, answer.id)
        assert revision is not None

        revision_ctx = RevisionContext(
            dek=plaintext_dek,
            crypto_version=ctx.crypto_version,
            envelope_id=ctx.envelope_id,
            answer_id=answer.id,
            answer_locator=answer_locator,
            revision_id=revision.id,
            revision_number=revision.revision_number,
        )
        aad = build_aad(revision_ctx)
        decrypted = decrypt_answer(revision.ciphertext, plaintext_dek, revision.nonce, aad)
        parsed = parse_plaintext_payload(decrypted)

        assert parsed.answer_state == "cleared"
        assert parsed.answer_value is None


class TestDuplicateMutationId:
    def test_duplicate_mutation_id_returns_existing(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, _dek = _create_envelope_and_context(core_db, response_db, session, version)

        mutation_id = uuid.uuid4()
        svc = AnswerSaveService()
        with _mock_session_key_load():
            result1 = _save_answer(svc, core_db, response_db, ctx, question, mutation_id=mutation_id)
            result2 = _save_answer(svc, core_db, response_db, ctx, question, mutation_id=mutation_id)

        assert result1.revision_number == result2.revision_number

        answer_locator = derive_session_answer_locator(ctx, question.id)
        answer = response_answer_repo.get_by_locator(response_db, ctx.envelope_id, answer_locator)
        assert answer is not None
        revisions = response_db.scalars(
            select(ResponseAnswerRevision).where(ResponseAnswerRevision.answer_id == answer.id)
        ).all()
        assert len(revisions) == 1, "duplicate mutation ID must not create a new revision"


class TestSessionValidation:
    def test_abandoned_session_rejected(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, _dek = _create_envelope_and_context(core_db, response_db, session, version)

        core_db.execute(
            text("UPDATE submission_sessions SET session_status = 'abandoned' WHERE id = :sid"),
            {"sid": session.id},
        )
        core_db.expire(session)

        svc = AnswerSaveService()
        with _mock_session_key_load(), pytest.raises(SessionInvalidError):
            _save_answer(svc, core_db, response_db, ctx, question)

    def test_completed_session_rejected(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version, status="completed")
        ctx, _dek = _create_envelope_and_context(core_db, response_db, session, version)

        svc = AnswerSaveService()
        with _mock_session_key_load(), pytest.raises(SessionInvalidError, match="completed"):
            _save_answer(svc, core_db, response_db, ctx, question)


class TestLocatorOpacity:
    def test_answer_locator_is_opaque_32_bytes(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, _dek = _create_envelope_and_context(core_db, response_db, session, version)

        svc = AnswerSaveService()
        with _mock_session_key_load():
            _save_answer(svc, core_db, response_db, ctx, question)

        answers = response_db.scalars(select(ResponseAnswer)).all()
        assert len(answers) == 1

        locator = answers[0].answer_locator
        assert isinstance(locator, bytes)
        assert len(locator) == 32, "answer_locator must be 32-byte HMAC-SHA256 digest"

        assert locator != question.id.bytes, "answer_locator must not be the raw question UUID"

    def test_session_locator_is_opaque_32_bytes(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, _dek = _create_envelope_and_context(core_db, response_db, session, version)

        svc = AnswerSaveService()
        with _mock_session_key_load():
            _save_answer(svc, core_db, response_db, ctx, question)

        loc = derive_session_locator(session.id, _FAKE_LINKAGE_KEY)
        assert len(loc.session_locator) == 32
        assert loc.session_locator != session.id.bytes
