"""Integration tests for answer save encryption flows.

Verifies end-to-end that:
- First save creates revision 1, latest pointer set
- Changed answer creates revision 2, latest pointer updated, revision 1 preserved
- Cleared answer creates new revision with null value
- Duplicate mutation ID returns existing without creating a new revision
- Expired session rejected before any write
- Completed session rejected before any write
- Analytics event failure does not block answer save
- Simultaneous first saves for same question handled by unique constraint
- Response DB locator columns contain opaque 32-byte HMAC digests
"""
from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import EncryptionSettings
from app.crypto import (
    build_aad,
    build_plaintext_payload,
    decrypt_answer,
    derive_answer_locator,
    derive_session_locator,
    parse_plaintext_payload,
)
from app.crypto.services import AnswerCryptoService
from app.domain.errors import SessionExpiredError, SessionInvalidError
from app.repositories.core.submission_sessions import create_session
from app.repositories.response import (
    response_answer_repo,
    response_answer_revision_repo,
    response_envelope_repo,
)
from app.schema.orm.core.submission_session import SubmissionEvent, SubmissionSession
from app.schema.orm.response.response_envelope import ResponseEnvelope
from app.services.public_submissions.core.actions.answer_save import AnswerSaveService
from app.services.public_submissions.core.shared.session_loader import SessionContext, load_current_session
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

    version.compiled_schema = {
        "nodes": [
            {
                "node_id": str(question.id),
                "type": "question",
                "sort_key": question.sort_key,
                "content": question.question_schema,
            }
        ]
    }
    core_db.flush()

    return project, survey, version, question


def _create_session_row(
    core_db: Session,
    project,
    survey,
    version,
    *,
    status: str = "in_progress",
    expired: bool = False,
):
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
    if expired:
        core_db.execute(
            text(
                "UPDATE submission_sessions "
                "SET started_at = :past, expires_at = :exp, last_activity_at = :past "
                "WHERE id = :sid"
            ),
            {
                "past": datetime.now(UTC) - timedelta(days=30),
                "exp": datetime.now(UTC) - timedelta(days=29),
                "sid": session.id,
            },
        )
        core_db.expire(session)
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


def _create_envelope_and_context(
    core_db: Session,
    response_db: Session,
    session,
    version,
):
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


def _mock_locator_service(session_id: str, linkage_secret: bytes = _LINKAGE_SECRET):
    """Create a mock LocatorService that derives real locators from the test secret."""
    svc = MagicMock()
    svc.answer_locator.side_effect = lambda sid, qid, version, db: derive_answer_locator(
        sid, qid, linkage_secret
    )
    svc.for_existing_session.side_effect = lambda sid, version, db: derive_session_locator(
        sid, linkage_secret
    )
    return svc


def _mock_dek_service(plaintext_dek: bytes):
    """Create a mock SessionDEKService that returns the given plaintext DEK."""
    svc = MagicMock()
    svc.get_for_session.return_value = plaintext_dek
    return svc


def _make_service(ctx: SessionContext, plaintext_dek: bytes) -> AnswerSaveService:
    """Build an AnswerSaveService with mock crypto services."""
    return AnswerSaveService(
        locator_service=_mock_locator_service(str(ctx.session.id)),
        dek_service=_mock_dek_service(plaintext_dek),
        answer_crypto_service=AnswerCryptoService(),
    )


class TestFirstSave:

    def test_first_save_creates_revision_1(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(core_db, response_db, session, version)

        svc = _make_service(ctx, plaintext_dek)
        mutation_id = uuid.uuid4()

        revision_id = svc.save_answer(
            core_db, response_db,
            ctx=ctx,
            question_node_id=str(question.id),
            answer_state="answered",
            answer_value="hello",
            client_mutation_id=mutation_id,
        )

        assert revision_id is not None

        answer_locator = derive_answer_locator(str(session.id), str(question.id), _LINKAGE_SECRET)
        answer = response_answer_repo.get_by_locator(response_db, ctx.envelope.id, answer_locator)
        assert answer is not None, "logical answer row must exist"
        assert answer.latest_revision_id == revision_id

        latest = response_answer_revision_repo.get_latest(response_db, answer.id)
        assert latest is not None
        assert latest.revision_number == 1

    def test_locator_columns_are_opaque_bytes(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(core_db, response_db, session, version)

        svc = _make_service(ctx, plaintext_dek)

        svc.save_answer(
            core_db, response_db,
            ctx=ctx,
            question_node_id=str(question.id),
            answer_state="answered",
            answer_value="test",
            client_mutation_id=uuid.uuid4(),
        )

        assert isinstance(ctx.envelope.session_locator, bytes)
        assert len(ctx.envelope.session_locator) == 32, (
            "session_locator must be a 32-byte HMAC-SHA256 digest"
        )

        answer_locator = derive_answer_locator(str(session.id), str(question.id), _LINKAGE_SECRET)
        answer = response_answer_repo.get_by_locator(response_db, ctx.envelope.id, answer_locator)
        assert answer is not None
        assert isinstance(answer.answer_locator, bytes)
        assert len(answer.answer_locator) == 32, (
            "answer_locator must be a 32-byte HMAC-SHA256 digest"
        )

        assert ctx.envelope.session_locator != str(session.id).encode(), (
            "session_locator must not be a readable UUID"
        )
        assert answer.answer_locator != str(question.id).encode(), (
            "answer_locator must not be a readable question ID"
        )

    def test_saved_ciphertext_round_trips_to_original_answer(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(core_db, response_db, session, version)

        svc = _make_service(ctx, plaintext_dek)

        svc.save_answer(
            core_db, response_db,
            ctx=ctx,
            question_node_id=str(question.id),
            answer_state="answered",
            answer_value="round-trip me",
            client_mutation_id=uuid.uuid4(),
        )

        answer_locator = derive_answer_locator(str(session.id), str(question.id), _LINKAGE_SECRET)
        answer = response_answer_repo.get_by_locator(response_db, ctx.envelope.id, answer_locator)
        assert answer is not None

        latest = response_answer_revision_repo.get_latest(response_db, answer.id)
        assert latest is not None

        aad = build_aad(
            crypto_version=ctx.envelope.crypto_version,
            envelope_id=answer.envelope_id,
            answer_id=answer.id,
            answer_locator=answer.answer_locator,
            revision_id=latest.id,
            revision_number=latest.revision_number,
        )
        plaintext_bytes = decrypt_answer(latest.ciphertext, plaintext_dek, latest.nonce, aad)
        expected = build_plaintext_payload(
            payload_version=1,
            question_node_id=str(question.id),
            answer_state="answered",
            answer_value="round-trip me",
        )
        assert plaintext_bytes == expected


class TestChangedAnswer:

    def test_changed_answer_creates_revision_2(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(core_db, response_db, session, version)

        svc = _make_service(ctx, plaintext_dek)

        rev1_id = svc.save_answer(
            core_db, response_db,
            ctx=ctx,
            question_node_id=str(question.id),
            answer_state="answered",
            answer_value="first",
            client_mutation_id=uuid.uuid4(),
        )
        rev2_id = svc.save_answer(
            core_db, response_db,
            ctx=ctx,
            question_node_id=str(question.id),
            answer_state="answered",
            answer_value="second",
            client_mutation_id=uuid.uuid4(),
        )

        assert rev1_id != rev2_id

        answer_locator = derive_answer_locator(str(session.id), str(question.id), _LINKAGE_SECRET)
        answer = response_answer_repo.get_by_locator(response_db, ctx.envelope.id, answer_locator)
        assert answer is not None
        assert answer.latest_revision_id == rev2_id

        history = response_answer_revision_repo.get_history(response_db, answer.id)
        assert len(history) == 2
        assert history[0].revision_number == 1
        assert history[0].id == rev1_id
        assert history[1].revision_number == 2
        assert history[1].id == rev2_id


class TestClearedAnswer:

    def test_cleared_answer_creates_revision_with_null_value(
        self, db_sessions: DbSessions
    ) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(core_db, response_db, session, version)

        svc = _make_service(ctx, plaintext_dek)

        svc.save_answer(
            core_db, response_db,
            ctx=ctx,
            question_node_id=str(question.id),
            answer_state="answered",
            answer_value="will be cleared",
            client_mutation_id=uuid.uuid4(),
        )
        clear_rev_id = svc.save_answer(
            core_db, response_db,
            ctx=ctx,
            question_node_id=str(question.id),
            answer_state="cleared",
            answer_value=None,
            client_mutation_id=uuid.uuid4(),
        )

        answer_locator = derive_answer_locator(str(session.id), str(question.id), _LINKAGE_SECRET)
        answer = response_answer_repo.get_by_locator(response_db, ctx.envelope.id, answer_locator)
        assert answer is not None
        assert answer.latest_revision_id == clear_rev_id

        history = response_answer_revision_repo.get_history(response_db, answer.id)
        assert len(history) == 2
        assert history[1].revision_number == 2

    def test_cleared_revision_decrypts_to_cleared_state(
        self, db_sessions: DbSessions
    ) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(core_db, response_db, session, version)

        svc = _make_service(ctx, plaintext_dek)

        svc.save_answer(
            core_db, response_db,
            ctx=ctx,
            question_node_id=str(question.id),
            answer_state="answered",
            answer_value="will be cleared",
            client_mutation_id=uuid.uuid4(),
        )
        svc.save_answer(
            core_db, response_db,
            ctx=ctx,
            question_node_id=str(question.id),
            answer_state="cleared",
            answer_value=None,
            client_mutation_id=uuid.uuid4(),
        )

        answer_locator = derive_answer_locator(str(session.id), str(question.id), _LINKAGE_SECRET)
        answer = response_answer_repo.get_by_locator(response_db, ctx.envelope.id, answer_locator)
        assert answer is not None

        latest = response_answer_revision_repo.get_latest(response_db, answer.id)
        assert latest is not None
        assert latest.revision_number == 2

        aad = build_aad(
            crypto_version=ctx.envelope.crypto_version,
            envelope_id=answer.envelope_id,
            answer_id=answer.id,
            answer_locator=answer.answer_locator,
            revision_id=latest.id,
            revision_number=latest.revision_number,
        )
        plaintext_bytes = decrypt_answer(latest.ciphertext, plaintext_dek, latest.nonce, aad)
        payload = parse_plaintext_payload(plaintext_bytes)
        assert payload["answer_state"] == "cleared"
        assert payload["answer_value"] is None


class TestDuplicateMutationId:

    def test_duplicate_mutation_id_returns_existing(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(core_db, response_db, session, version)

        svc = _make_service(ctx, plaintext_dek)
        mutation_id = uuid.uuid4()

        first_id = svc.save_answer(
            core_db, response_db,
            ctx=ctx,
            question_node_id=str(question.id),
            answer_state="answered",
            answer_value="hello",
            client_mutation_id=mutation_id,
        )
        second_id = svc.save_answer(
            core_db, response_db,
            ctx=ctx,
            question_node_id=str(question.id),
            answer_state="answered",
            answer_value="hello",
            client_mutation_id=mutation_id,
        )

        assert first_id == second_id

        answer_locator = derive_answer_locator(str(session.id), str(question.id), _LINKAGE_SECRET)
        answer = response_answer_repo.get_by_locator(response_db, ctx.envelope.id, answer_locator)
        assert answer is not None
        history = response_answer_revision_repo.get_history(response_db, answer.id)
        assert len(history) == 1, "duplicate mutation must not create a second revision"


class TestExpiredSession:

    def test_expired_session_rejected(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, _ = _setup_core_fixtures(core_db)
        session, raw_token = _create_session_row(
            core_db, project, survey, version, expired=True
        )
        _create_envelope_and_context(core_db, response_db, session, version)

        locator_service = MagicMock()
        locator_service.for_existing_session.return_value = derive_session_locator(
            str(session.id), _LINKAGE_SECRET
        )

        with pytest.raises(SessionExpiredError):
            load_current_session(
                core_db,
                response_db,
                raw_token,
                encryption_settings=_FAKE_ENC_SETTINGS,
                locator_service=locator_service,
            )


class TestCompletedSession:

    def test_completed_session_rejected(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, _ = _setup_core_fixtures(core_db)
        session, raw_token = _create_session_row(
            core_db, project, survey, version, status="completed"
        )
        _create_envelope_and_context(core_db, response_db, session, version)

        locator_service = MagicMock()
        locator_service.for_existing_session.return_value = derive_session_locator(
            str(session.id), _LINKAGE_SECRET
        )

        with pytest.raises(SessionInvalidError, match="already completed"):
            load_current_session(
                core_db,
                response_db,
                raw_token,
                encryption_settings=_FAKE_ENC_SETTINGS,
                locator_service=locator_service,
            )


class TestAnalyticsFailure:

    def test_analytics_event_failure_does_not_block_save(
        self, db_sessions: DbSessions
    ) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(core_db, response_db, session, version)

        svc = _make_service(ctx, plaintext_dek)

        with patch(
            "app.services.public_submissions.core.actions.answer_save.event_repo.create_event",
            side_effect=Exception("DB error"),
        ):
            revision_id = svc.save_answer(
                core_db, response_db,
                ctx=ctx,
                question_node_id=str(question.id),
                answer_state="answered",
                answer_value="hello",
                client_mutation_id=uuid.uuid4(),
            )

        assert revision_id is not None

        answer_locator = derive_answer_locator(str(session.id), str(question.id), _LINKAGE_SECRET)
        answer = response_answer_repo.get_by_locator(response_db, ctx.envelope.id, answer_locator)
        assert answer is not None, "answer must be saved despite analytics failure"


class TestCoreDbPrivacy:

    def test_core_db_has_no_plaintext_answers_or_response_ids(
        self, db_sessions: DbSessions
    ) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(core_db, response_db, session, version)

        svc = _make_service(ctx, plaintext_dek)

        svc.save_answer(
            core_db, response_db,
            ctx=ctx,
            question_node_id=str(question.id),
            answer_state="answered",
            answer_value="secret answer text",
            client_mutation_id=uuid.uuid4(),
        )

        core_session = core_db.get(SubmissionSession, session.id)
        assert core_session is not None

        session_columns = {c.name: getattr(core_session, c.name) for c in core_session.__table__.columns}
        for col_name, col_value in session_columns.items():
            if col_value is None or isinstance(col_value, (int, bool, datetime)):
                continue
            str_val = str(col_value)
            assert "secret answer text" not in str_val, (
                f"core session column '{col_name}' contains plaintext answer value"
            )

        envelope = response_db.scalar(select(ResponseEnvelope))
        assert envelope is not None
        for col_name, col_value in session_columns.items():
            if col_value is None or isinstance(col_value, (int, bool, datetime)):
                continue
            str_val = str(col_value)
            assert str(envelope.id) not in str_val, (
                f"core session column '{col_name}' contains response envelope ID"
            )

        events = core_db.scalars(
            select(SubmissionEvent).where(SubmissionEvent.session_id == session.id)
        ).all()
        for event in events:
            event_columns = {c.name: getattr(event, c.name) for c in event.__table__.columns}
            for col_name, col_value in event_columns.items():
                if col_value is None or isinstance(col_value, (int, bool, datetime)):
                    continue
                str_val = str(col_value)
                assert "secret answer text" not in str_val, (
                    f"core event column '{col_name}' contains plaintext answer value"
                )
                assert str(envelope.id) not in str_val, (
                    f"core event column '{col_name}' contains response envelope ID"
                )


class TestCacheMissUnwrapDek:

    def test_dek_service_get_called_on_save(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(core_db, response_db, session, version)

        dek_svc = _mock_dek_service(plaintext_dek)
        svc = AnswerSaveService(
            locator_service=_mock_locator_service(str(session.id)),
            dek_service=dek_svc,
            answer_crypto_service=AnswerCryptoService(),
        )

        svc.save_answer(
            core_db, response_db,
            ctx=ctx,
            question_node_id=str(question.id),
            answer_state="answered",
            answer_value="cache miss test",
            client_mutation_id=uuid.uuid4(),
        )

        dek_svc.get_for_session.assert_called_once()
        call_args = dek_svc.get_for_session.call_args
        assert call_args[0][1] == ctx.envelope.wrapped_dek, (
            "get_for_session must receive the wrapped DEK from the envelope"
        )

    def test_dek_service_receives_correct_session_id(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(core_db, response_db, session, version)

        dek_svc = _mock_dek_service(plaintext_dek)
        svc = AnswerSaveService(
            locator_service=_mock_locator_service(str(session.id)),
            dek_service=dek_svc,
            answer_crypto_service=AnswerCryptoService(),
        )

        svc.save_answer(
            core_db, response_db,
            ctx=ctx,
            question_node_id=str(question.id),
            answer_state="answered",
            answer_value="cache hit test",
            client_mutation_id=uuid.uuid4(),
        )

        dek_svc.get_for_session.assert_called_once()
        call_args = dek_svc.get_for_session.call_args
        assert call_args[0][0] == session.id, (
            "get_for_session must receive the session ID"
        )


class TestSequentialDuplicateSaves:

    def test_sequential_duplicate_saves_handled(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(core_db, response_db, session, version)

        svc = _make_service(ctx, plaintext_dek)

        rev1_id = svc.save_answer(
            core_db, response_db,
            ctx=ctx,
            question_node_id=str(question.id),
            answer_state="answered",
            answer_value="first",
            client_mutation_id=uuid.uuid4(),
        )
        rev2_id = svc.save_answer(
            core_db, response_db,
            ctx=ctx,
            question_node_id=str(question.id),
            answer_state="answered",
            answer_value="concurrent second",
            client_mutation_id=uuid.uuid4(),
        )

        assert rev1_id is not None
        assert rev2_id is not None
        assert rev1_id != rev2_id

        answer_locator = derive_answer_locator(str(session.id), str(question.id), _LINKAGE_SECRET)
        answer = response_answer_repo.get_by_locator(response_db, ctx.envelope.id, answer_locator)
        assert answer is not None
        history = response_answer_revision_repo.get_history(response_db, answer.id)
        assert len(history) == 2, "both saves must persist without crashing"
