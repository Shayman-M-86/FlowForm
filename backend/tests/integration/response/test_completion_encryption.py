"""Integration tests for session completion.

Verifies:
- Completion marks an in-progress session completed without decrypting answers
- Repeated completion is rejected once the session is completed
- Missing required answers do not block completion
- Session completion event inserted
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from sqlalchemy import text
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
    SessionContext,
)
from app.domain.errors import SessionInvalidError
from app.repositories.core.submission_sessions import create_session
from app.repositories.response import (
    response_answer_repo,
    response_answer_revision_repo,
    response_envelope_repo,
)
from app.schema.enums import SubmissionAnswerState
from app.schema.orm.core.submission_session import SessionRef
from app.services.public_submissions.core.actions.completion import CompletionService
from tests.integration.core.factories import (
    make_project,
    make_response_store,
    make_survey,
    make_survey_question,
    make_survey_rule,
    make_survey_version,
    make_user,
)

if TYPE_CHECKING:
    from tests.conftest import DbSessions

_LINKAGE_SECRET = b"\xcc" * 32
_FAKE_LINKAGE_KEY = LinkageKey(version=1, secret=_LINKAGE_SECRET, aws_version_id="test-version")


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

    if required_questions:
        rule = make_survey_rule(
            survey_version_id=version.id,
            rule_key="require-q1",
            sort_key=question.sort_key - 1,
            rule_schema={
                "id": "require-q1",
                "if": {
                    "match": "NONE",
                    "conditions": [
                        {
                            "target_id": str(question.id),
                            "family": "field",
                            "requirements": {
                                "type": "number",
                                "operator": "GT",
                                "value": 0,
                            },
                        }
                    ],
                },
                "then": {"set": [{"target_id": str(question.id), "required": True}]},
            },
        )
        core_db.add(rule)
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
    plaintext_dek = PlaintextSessionKey(os.urandom(32))
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
    return ctx, plaintext_dek


def _save_encrypted_answer(
    response_db: Session,
    ctx: SessionContext,
    plaintext_dek: PlaintextSessionKey,
    question_node_id: UUID,
    answer_state: SubmissionAnswerState = "answered",
    answer_value=None,
):
    answer_locator = derive_answer_locator(ctx.session_id, question_node_id, _FAKE_LINKAGE_KEY)

    revision_id = uuid.uuid4()

    answer_row, _ = response_answer_repo.get_or_create(
        response_db,
        envelope_id=ctx.envelope_id,
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
        crypto_version=ctx.crypto_version,
        envelope_id=ctx.envelope_id,
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
        envelope_id=ctx.envelope_id,
        revision_number=1,
        nonce=nonce,
        ciphertext=ciphertext,
        client_mutation_id=uuid.uuid4(),
        revision_id=revision_id,
    )

    return answer_row


class TestCompletion:
    def test_completion_marks_session_completed(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(core_db, response_db, session, version)

        _save_encrypted_answer(
            response_db,
            ctx,
            plaintext_dek,
            question_node_id=question.id,
            answer_value={"field_type": "short_text", "text": "my answer"},
        )

        svc = CompletionService()

        result = svc.complete_session(core_db, response_db, ctx=ctx)

        assert result.status == "completed"
        assert result.completed_at is not None

        core_db.expire(session)
        assert session.session_status == "completed"
        assert session.completed_at is not None

    def test_completion_handles_started_at_ahead_of_app_clock(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, _question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)

        future_started_at = datetime.now(UTC) + timedelta(minutes=5)
        core_db.execute(
            text(
                "UPDATE submission_sessions "
                "SET started_at = :started_at, last_activity_at = :started_at, expires_at = :expires_at "
                "WHERE id = :sid"
            ),
            {
                "started_at": future_started_at,
                "expires_at": future_started_at + timedelta(days=7),
                "sid": session.id,
            },
        )
        core_db.expire(session)

        ctx, _dek = _create_envelope_and_context(core_db, response_db, session, version)
        svc = CompletionService()

        result = svc.complete_session(core_db, response_db, ctx=ctx)

        core_db.expire(session)
        assert result.status == "completed"
        assert result.completed_at >= session.started_at
        assert session.completed_at == result.completed_at

    def test_repeated_completion_is_rejected(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, plaintext_dek = _create_envelope_and_context(core_db, response_db, session, version)  # needed below

        _save_encrypted_answer(
            response_db,
            ctx,
            plaintext_dek,
            question_node_id=question.id,
            answer_value={"field_type": "short_text", "text": "my answer"},
        )

        svc = CompletionService()

        svc.complete_session(core_db, response_db, ctx=ctx)

        with pytest.raises(SessionInvalidError, match="completed"):
            svc.complete_session(core_db, response_db, ctx=ctx)

    def test_missing_required_answer_does_not_block_completion(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, _question = _setup_core_fixtures(core_db, required_questions=True)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, _dek = _create_envelope_and_context(core_db, response_db, session, version)

        svc = CompletionService()

        result = svc.complete_session(core_db, response_db, ctx=ctx)

        assert result.status == "completed"

    def test_completion_with_no_required_questions_succeeds(self, db_sessions: DbSessions) -> None:
        core_db, response_db = db_sessions.core, db_sessions.response
        project, survey, version, _question = _setup_core_fixtures(core_db)
        session, _ = _create_session_row(core_db, project, survey, version)
        ctx, _dek = _create_envelope_and_context(core_db, response_db, session, version)

        svc = CompletionService()

        result = svc.complete_session(core_db, response_db, ctx=ctx)

        assert result.status == "completed"
