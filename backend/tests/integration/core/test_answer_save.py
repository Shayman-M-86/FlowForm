"""Integration tests for AnswerSaveService and question-viewed event."""
from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from app.crypto.dek_cache import DekCache
from app.db.error_handling import commit_with_err_handle
from app.domain.errors import QuestionNotInVersionError, SessionInvalidError
from app.repositories.response import (
    response_answer_repo,
    response_answer_revision_repo,
    response_envelope_repo,
)
from app.services.public_submissions.core.answer_save import AnswerSaveService
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


def _fake_encryption_settings() -> MagicMock:
    enc = MagicMock()
    enc.linkage_secret_arn = "arn:aws:secretsmanager:us-east-1:000:secret:test"
    enc.kms_key_arn = "arn:aws:kms:us-east-1:000:key/test"
    enc.aws_region = "us-east-1"
    enc.aws_access_key_id = MagicMock()
    enc.aws_secret_access_key = MagicMock()
    return enc


def _setup_core_fixtures(core_db):
    """Create user, project, survey, version, question in core DB."""
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


def _create_session_row(core_db, project, survey, version):
    """Create a submission session row directly."""
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
    )
    return session, raw_token


def _create_envelope_and_context(
    core_db, response_db, session, version, *, dek_cache=None
):
    """Create a response envelope and build a SessionContext."""
    session_locator = os.urandom(32)
    plaintext_dek = os.urandom(32)
    wrapped_dek = os.urandom(64)

    envelope = response_envelope_repo.create(
        response_db,
        session_locator=session_locator,
        linkage_key_version=1,
        wrapped_dek=wrapped_dek,
        kms_key_arn="arn:aws:kms:us-east-1:000:key/test",
        kms_context_version=1,
        crypto_version=1,
    )

    enc = _fake_encryption_settings()

    ctx = SessionContext(
        session=session,
        survey_version=version,
        session_locator=session_locator,
        envelope=envelope,
        encryption_settings=enc,
    )
    return ctx, plaintext_dek


class TestAnswerSave:
    def test_save_answer_creates_revision(self, db_sessions: DbSessions) -> None:
        core_db = db_sessions.core
        response_db = db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(
            core_db, response_db, session, version
        )

        dek_cache = DekCache()
        dek_cache.put(ctx.session_locator, plaintext_dek)
        svc = AnswerSaveService(dek_cache=dek_cache)

        mutation_id = uuid.uuid4()
        with patch(
            "app.services.public_submissions.core.answer_save.get_linkage_secret",
            return_value=b"\x01" * 32,
        ), patch(
            "app.services.public_submissions.core.answer_save.derive_answer_locator",
            return_value=os.urandom(32),
        ):
            revision_id = svc.save_answer(
                core_db,
                response_db,
                ctx=ctx,
                question_node_id=str(question.id),
                answer_state="answered",
                answer_value="hello",
                client_mutation_id=mutation_id,
            )

        assert revision_id is not None

    def test_mutation_id_dedup_returns_existing(
        self, db_sessions: DbSessions
    ) -> None:
        core_db = db_sessions.core
        response_db = db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(
            core_db, response_db, session, version
        )

        dek_cache = DekCache()
        dek_cache.put(ctx.session_locator, plaintext_dek)
        svc = AnswerSaveService(dek_cache=dek_cache)

        mutation_id = uuid.uuid4()
        answer_locator = os.urandom(32)

        with patch(
            "app.services.public_submissions.core.answer_save.get_linkage_secret",
            return_value=b"\x01" * 32,
        ), patch(
            "app.services.public_submissions.core.answer_save.derive_answer_locator",
            return_value=answer_locator,
        ):
            first_id = svc.save_answer(
                core_db,
                response_db,
                ctx=ctx,
                question_node_id=str(question.id),
                answer_state="answered",
                answer_value="hello",
                client_mutation_id=mutation_id,
            )
            second_id = svc.save_answer(
                core_db,
                response_db,
                ctx=ctx,
                question_node_id=str(question.id),
                answer_state="answered",
                answer_value="hello",
                client_mutation_id=mutation_id,
            )

        assert first_id == second_id

    def test_question_not_in_version_raises(
        self, db_sessions: DbSessions
    ) -> None:
        core_db = db_sessions.core
        response_db = db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(
            core_db, response_db, session, version
        )

        dek_cache = DekCache()
        dek_cache.put(ctx.session_locator, plaintext_dek)
        svc = AnswerSaveService(dek_cache=dek_cache)

        bogus_question_id = str(uuid.uuid4())
        with patch(
            "app.services.public_submissions.core.answer_save.get_linkage_secret",
            return_value=b"\x01" * 32,
        ), patch(
            "app.services.public_submissions.core.answer_save.derive_answer_locator",
            return_value=os.urandom(32),
        ), pytest.raises(QuestionNotInVersionError):
            svc.save_answer(
                core_db,
                response_db,
                ctx=ctx,
                question_node_id=bogus_question_id,
                answer_state="answered",
                answer_value="hello",
                client_mutation_id=uuid.uuid4(),
            )

    def test_analytics_failure_does_not_raise(
        self, db_sessions: DbSessions
    ) -> None:
        core_db = db_sessions.core
        response_db = db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(
            core_db, response_db, session, version
        )

        dek_cache = DekCache()
        dek_cache.put(ctx.session_locator, plaintext_dek)
        svc = AnswerSaveService(dek_cache=dek_cache)

        mutation_id = uuid.uuid4()
        with patch(
            "app.services.public_submissions.core.answer_save.get_linkage_secret",
            return_value=b"\x01" * 32,
        ), patch(
            "app.services.public_submissions.core.answer_save.derive_answer_locator",
            return_value=os.urandom(32),
        ), patch(
            "app.services.public_submissions.core.answer_save.event_repo.create_event",
            side_effect=Exception("DB error"),
        ):
            revision_id = svc.save_answer(
                core_db,
                response_db,
                ctx=ctx,
                question_node_id=str(question.id),
                answer_state="answered",
                answer_value="hello",
                client_mutation_id=mutation_id,
            )

        assert revision_id is not None


class TestQuestionViewed:
    def test_record_question_viewed_succeeds(
        self, db_sessions: DbSessions
    ) -> None:
        core_db = db_sessions.core
        response_db = db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, _ = _create_envelope_and_context(
            core_db, response_db, session, version
        )

        svc = AnswerSaveService()
        svc.record_question_viewed(
            core_db, ctx=ctx, question_node_id=str(question.id)
        )

    def test_record_question_viewed_invalid_question_raises(
        self, db_sessions: DbSessions
    ) -> None:
        core_db = db_sessions.core
        response_db = db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, _ = _create_envelope_and_context(
            core_db, response_db, session, version
        )

        svc = AnswerSaveService()
        with pytest.raises(QuestionNotInVersionError):
            svc.record_question_viewed(
                core_db, ctx=ctx, question_node_id=str(uuid.uuid4())
            )

    def test_record_question_viewed_event_write_failure_swallowed(
        self, db_sessions: DbSessions
    ) -> None:
        core_db = db_sessions.core
        response_db = db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, _ = _create_envelope_and_context(
            core_db, response_db, session, version
        )

        svc = AnswerSaveService()
        with patch(
            "app.services.public_submissions.core.answer_save.event_repo.create_event",
            side_effect=Exception("DB write failure"),
        ):
            svc.record_question_viewed(
                core_db, ctx=ctx, question_node_id=str(question.id)
            )


class TestAnalyticsCoreCommitFailure:
    def test_core_commit_failure_does_not_block_save(
        self, db_sessions: DbSessions
    ) -> None:
        """Step 12: if core commit fails after the analytics event insert,
        the response write (step 10) is already committed and the revision
        ID must still be returned."""
        core_db = db_sessions.core
        response_db = db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(
            core_db, response_db, session, version
        )

        dek_cache = DekCache()
        dek_cache.put(ctx.session_locator, plaintext_dek)
        svc = AnswerSaveService(dek_cache=dek_cache)

        real_commit = commit_with_err_handle
        call_count = 0

        def commit_failing_on_core(db, *, contexts):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("Core commit failure after event insert")
            real_commit(db, contexts=contexts)

        mutation_id = uuid.uuid4()
        with patch(
            "app.services.public_submissions.core.answer_save.get_linkage_secret",
            return_value=b"\x01" * 32,
        ), patch(
            "app.services.public_submissions.core.answer_save.derive_answer_locator",
            return_value=os.urandom(32),
        ), patch(
            "app.services.public_submissions.core.answer_save.commit_with_err_handle",
            side_effect=commit_failing_on_core,
        ):
            revision_id = svc.save_answer(
                core_db,
                response_db,
                ctx=ctx,
                question_node_id=str(question.id),
                answer_state="answered",
                answer_value="hello",
                client_mutation_id=mutation_id,
            )

        assert revision_id is not None
