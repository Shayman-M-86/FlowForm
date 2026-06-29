"""Integration tests for AnswerSaveService and question-viewed event."""

from __future__ import annotations

import os
import uuid
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from app.crypto.answers import derive_slot_answer_locator
from app.crypto.locators import derive_session_locator
from app.crypto.models import LinkageKey, PlaintextSessionKey, SubmissionSessionContext
from app.domain.errors import QuestionNotInVersionError
from app.repositories.response import response_envelope_repo
from app.schema.orm.core import SubmissionAnswerSlot
from app.schema.orm.response import ResponseAnswer
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

def _setup_core_fixtures(core_db):
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


def _create_session_row(core_db, project, survey, version):
    from app.repositories.core.submission_sessions import create_session

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
    return session, raw_token


def _create_envelope_and_context(core_db, response_db, session, version):
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

    ctx = SubmissionSessionContext(
        session_id=session.id,
        project_id=session.project_id,
        survey_id=session.survey_id,
        survey_version_id=version.id,
        envelope_id=envelope.id,
        session_locator=session_locator,
        linkage_key=_FAKE_LINKAGE_KEY,
        linkage_key_version=_FAKE_LINKAGE_KEY.version,
        _session_dek=_FAKE_PLAINTEXT_DEK,
        crypto_version=1,
        expires_at=session.expires_at,
        browser_session_token_hash=session.browser_session_token_hash,
    )
    return ctx, _FAKE_PLAINTEXT_DEK


class TestAnswerSave:
    def test_save_answer_creates_revision(self, db_sessions: DbSessions) -> None:
        core_db = db_sessions.core
        response_db = db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, _dek = _create_envelope_and_context(core_db, response_db, session, version)

        svc = AnswerSaveService()
        mutation_id = uuid.uuid4()
        result = svc.save_answer(
            core_db,
            response_db,
            ctx=ctx,
            question_node_id=question.id,
            answer_state="answered",
            answer_value={"field_type": "short_text", "text": "hello"},
            client_mutation_id=mutation_id,
        )

        assert result is not None

    def test_mutation_id_dedup_returns_existing(self, db_sessions: DbSessions) -> None:
        core_db = db_sessions.core
        response_db = db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, _dek = _create_envelope_and_context(core_db, response_db, session, version)

        svc = AnswerSaveService()
        mutation_id = uuid.uuid4()

        first = svc.save_answer(
            core_db, response_db, ctx=ctx,
            question_node_id=question.id, answer_state="answered",
            answer_value={"field_type": "short_text", "text": "hello"},
            client_mutation_id=mutation_id,
        )
        second = svc.save_answer(
            core_db, response_db, ctx=ctx,
            question_node_id=question.id, answer_state="answered",
            answer_value={"field_type": "short_text", "text": "hello"},
            client_mutation_id=mutation_id,
        )

        assert first == second

    def test_analytics_rollback_does_not_orphan_response_answer(
        self,
        db_sessions: DbSessions,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        core_db = db_sessions.core
        response_db = db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, _dek = _create_envelope_and_context(core_db, response_db, session, version)

        def _analytics_failure_rollback(db, **_kwargs) -> None:
            db.rollback()

        monkeypatch.setattr(
            f"{_ANSWER_SAVE_MODULE}.event_repo.record_event",
            _analytics_failure_rollback,
        )

        svc = AnswerSaveService()

        svc.save_answer(
            core_db,
            response_db,
            ctx=ctx,
            question_node_id=question.id,
            answer_state="answered",
            answer_value={"field_type": "short_text", "text": "hello"},
            client_mutation_id=uuid.uuid4(),
        )

        slot = core_db.scalar(
            select(SubmissionAnswerSlot).where(
                SubmissionAnswerSlot.submission_session_id == session.id,
                SubmissionAnswerSlot.question_node_id == question.id,
            )
        )
        assert slot is not None
        answer_locator = derive_slot_answer_locator(slot.id, ctx.linkage_key)
        assert response_db.get(ResponseAnswer, answer_locator) is not None

        svc.save_answer(
            core_db,
            response_db,
            ctx=ctx,
            question_node_id=question.id,
            answer_state="answered",
            answer_value={"field_type": "short_text", "text": "hello again"},
            client_mutation_id=uuid.uuid4(),
        )

        slots = list(
            core_db.scalars(
                select(SubmissionAnswerSlot).where(
                    SubmissionAnswerSlot.submission_session_id == session.id,
                    SubmissionAnswerSlot.question_node_id == question.id,
                )
            )
        )
        answers = list(
            response_db.scalars(select(ResponseAnswer).where(ResponseAnswer.envelope_id == ctx.envelope_id))
        )

        assert [saved_slot.id for saved_slot in slots] == [slot.id]
        assert [answer.answer_locator for answer in answers] == [answer_locator]

    def test_question_not_in_version_raises(self, db_sessions: DbSessions) -> None:
        core_db = db_sessions.core
        response_db = db_sessions.response
        project, survey, version, _question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, _dek = _create_envelope_and_context(core_db, response_db, session, version)

        svc = AnswerSaveService()
        with pytest.raises(QuestionNotInVersionError):
            svc.save_answer(
                core_db, response_db, ctx=ctx,
                question_node_id=uuid.uuid4(), answer_state="answered",
                answer_value={"field_type": "short_text", "text": "hello"},
                client_mutation_id=uuid.uuid4(),
            )

class TestQuestionViewed:
    def test_record_question_viewed_succeeds(self, db_sessions: DbSessions) -> None:
        core_db = db_sessions.core
        response_db = db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, _ = _create_envelope_and_context(core_db, response_db, session, version)

        svc = AnswerSaveService()
        svc.record_question_viewed(core_db, ctx=ctx, question_node_id=question.id)

    def test_record_question_viewed_invalid_question_raises(self, db_sessions: DbSessions) -> None:
        core_db = db_sessions.core
        response_db = db_sessions.response
        project, survey, version, _question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, _ = _create_envelope_and_context(core_db, response_db, session, version)

        svc = AnswerSaveService()
        with pytest.raises(QuestionNotInVersionError):
            svc.record_question_viewed(core_db, ctx=ctx, question_node_id=uuid.uuid4())

    def test_record_question_viewed_event_succeeds_normally(self, db_sessions: DbSessions) -> None:
        core_db = db_sessions.core
        response_db = db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, _ = _create_envelope_and_context(core_db, response_db, session, version)

        svc = AnswerSaveService()
        svc.record_question_viewed(core_db, ctx=ctx, question_node_id=question.id)
