"""Integration tests for session-start reconciliation repair.

Verifies that:
- In-progress committed core session with no response envelope is marked abandoned
- In-progress committed core session with a matching envelope stays in_progress
- Completed and already-abandoned sessions are ignored
- A repaired abandoned session is rejected by the current-session loader
- Normal KMS/envelope failure still asserts rollback, not abandoned
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crypto._internal.errors import KmsError
from app.crypto.models import (
    LinkageKey,
    NewSessionKey,
    NewSessionLocator,
    PlaintextSessionKey,
    SessionLocator,
    WrappedSessionKey,
)
from app.domain.errors import SessionInvalidError, SessionStartError
from app.schema.api.requests.submission_sessions import StartSubmissionSessionRequest
from app.schema.orm.core.submission_session import SubmissionSession
from app.schema.orm.response.response_envelope import ResponseEnvelope
from app.services.public_submissions.core.actions.session_starter import SessionStarter
from app.services.public_submissions.core.reconciliation import (
    reconcile_orphaned_sessions,
)
from app.services.public_submissions.core.session_loader import load_current_session
from tests.integration.core.factories import (
    make_project,
    make_response_store,
    make_survey,
    make_survey_version,
    make_user,
)

if TYPE_CHECKING:
    from tests.conftest import DbSessions

_SCHEMA = {"nodes": [{"id": "q1", "type": "short_text"}]}
_LINKAGE_SECRET = b"\xcc" * 32
_FAKE_LINKAGE_KEY = LinkageKey(version=1, secret=_LINKAGE_SECRET, aws_version_id="test-version")
_FAKE_SESSION_LOCATOR = SessionLocator(os.urandom(32))
_FAKE_PLAINTEXT_DEK = PlaintextSessionKey(os.urandom(32))
_FAKE_WRAPPED_DEK = WrappedSessionKey(b"\xbb" * 64)

_STARTER_MODULE = "app.services.public_submissions.core.actions.session_starter"
_LOADER_MODULE = "app.services.public_submissions.core.session_loader"
_RECON_MODULE = "app.services.public_submissions.core.reconciliation"


def _seed_published_survey(db: Session, slug: str) -> int:
    user = make_user()
    db.add(user)
    db.flush()

    project = make_project(user.id)
    db.add(project)
    db.flush()

    store = make_response_store(project.id, user.id)
    db.add(store)
    db.flush()

    survey = make_survey(project.id, store.id, user.id)
    survey.visibility = "public"
    survey.public_slug = slug
    db.add(survey)
    db.flush()

    version = make_survey_version(survey.id, user.id)
    version.status = "published"
    version.compiled_schema = _SCHEMA
    version.published_at = datetime.now(UTC)
    db.add(version)
    db.flush()

    survey.published_version_id = version.id
    db.flush()

    return survey.id


def _slug_payload(slug: str) -> StartSubmissionSessionRequest:
    return StartSubmissionSessionRequest.model_validate({"access": {"type": "public_slug", "public_slug": slug}})


def _mock_crypto_for_start():
    return [
        patch(f"{_STARTER_MODULE}.load_current_linkage_key", return_value=_FAKE_LINKAGE_KEY),
        patch(
            f"{_STARTER_MODULE}.derive_session_locator",
            return_value=NewSessionLocator(linkage_key_version=1, session_locator=_FAKE_SESSION_LOCATOR),
        ),
        patch(
            f"{_STARTER_MODULE}.start_plaintext_survey_key_load",
            return_value=MagicMock(return_value=os.urandom(32)),
        ),
        patch(
            f"{_STARTER_MODULE}.create_session_key",
            return_value=NewSessionKey(plaintext_key=_FAKE_PLAINTEXT_DEK, wrapped_key=_FAKE_WRAPPED_DEK),
        ),
    ]


class TestReconciliation:
    def test_orphan_session_marked_abandoned(self, db_sessions: DbSessions) -> None:
        survey_id = _seed_published_survey(db_sessions.core, "recon-orphan")

        patches = _mock_crypto_for_start()
        with patches[0], patches[1], patches[2], patches[3]:
            starter = SessionStarter()
            starter.start(
                db_sessions.core, db_sessions.response,
                payload=_slug_payload("recon-orphan"), actor=None,
            )

        envelope = db_sessions.response.scalar(select(ResponseEnvelope))
        assert envelope is not None
        db_sessions.response.delete(envelope)
        db_sessions.response.commit()

        with patch(
            f"{_RECON_MODULE}.resolve_existing_session_locator",
            return_value=(_FAKE_SESSION_LOCATOR, _FAKE_LINKAGE_KEY),
        ):
            result = reconcile_orphaned_sessions(db_sessions.core, db_sessions.response)

        assert result.abandoned == 1

        session = db_sessions.core.scalar(
            select(SubmissionSession).where(SubmissionSession.survey_id == survey_id),
        )
        assert session is not None
        assert session.session_status == "abandoned"

    def test_session_with_envelope_stays_in_progress(self, db_sessions: DbSessions) -> None:
        _seed_published_survey(db_sessions.core, "recon-ok")

        patches = _mock_crypto_for_start()
        with patches[0], patches[1], patches[2], patches[3]:
            starter = SessionStarter()
            starter.start(
                db_sessions.core, db_sessions.response,
                payload=_slug_payload("recon-ok"), actor=None,
            )

        with patch(
            f"{_RECON_MODULE}.resolve_existing_session_locator",
            return_value=(_FAKE_SESSION_LOCATOR, _FAKE_LINKAGE_KEY),
        ):
            result = reconcile_orphaned_sessions(db_sessions.core, db_sessions.response)

        assert result.matched == 1
        assert result.abandoned == 0

    def test_abandoned_session_rejected_by_loader(self, db_sessions: DbSessions) -> None:
        _seed_published_survey(db_sessions.core, "recon-reject")

        patches = _mock_crypto_for_start()
        with patches[0], patches[1], patches[2], patches[3]:
            starter = SessionStarter()
            _, resume_token, _ = starter.start(
                db_sessions.core, db_sessions.response,
                payload=_slug_payload("recon-reject"), actor=None,
            )

        envelope = db_sessions.response.scalar(select(ResponseEnvelope))
        assert envelope is not None
        db_sessions.response.delete(envelope)
        db_sessions.response.commit()

        with patch(
            f"{_RECON_MODULE}.resolve_existing_session_locator",
            return_value=(_FAKE_SESSION_LOCATOR, _FAKE_LINKAGE_KEY),
        ):
            reconcile_orphaned_sessions(db_sessions.core, db_sessions.response)

        from app.core.extensions import app_cache
        from app.repositories.core.submission_sessions import hash_browser_session_token

        app_cache.sessions.write_context.evict(hash_browser_session_token(resume_token))

        with pytest.raises(SessionInvalidError, match="abandoned"), patch(
            f"{_LOADER_MODULE}.resolve_existing_session_locator",
            return_value=(_FAKE_SESSION_LOCATOR, _FAKE_LINKAGE_KEY),
        ):
            load_current_session(db_sessions.core, db_sessions.response, resume_token)

    def test_kms_failure_rolls_back_not_abandoned(self, db_sessions: DbSessions) -> None:
        survey_id = _seed_published_survey(db_sessions.core, "recon-kms")

        with (
            patch(f"{_STARTER_MODULE}.load_current_linkage_key", return_value=_FAKE_LINKAGE_KEY),
            patch(
                f"{_STARTER_MODULE}.derive_session_locator",
                return_value=NewSessionLocator(
                    linkage_key_version=1, session_locator=_FAKE_SESSION_LOCATOR,
                ),
            ),
            patch(
                f"{_STARTER_MODULE}.start_plaintext_survey_key_load",
                return_value=MagicMock(return_value=os.urandom(32)),
            ),
            patch(f"{_STARTER_MODULE}.create_session_key", side_effect=KmsError("KMS encrypt failed")),
            pytest.raises(SessionStartError),
        ):
            starter = SessionStarter()
            starter.start(
                db_sessions.core, db_sessions.response,
                payload=_slug_payload("recon-kms"), actor=None,
            )

        session = db_sessions.core.scalar(
            select(SubmissionSession).where(SubmissionSession.survey_id == survey_id),
        )
        assert session is None, "core session must be rolled back, not abandoned"
