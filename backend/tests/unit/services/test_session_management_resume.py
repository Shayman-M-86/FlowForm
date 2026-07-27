from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from app.domain.errors import SessionNotFoundError
from app.schema.api.requests.submission_sessions import StartSubmissionSessionRequest
from app.services.public_submissions.api.session_management import (
    SessionManagementService,
)


def _survey() -> SimpleNamespace:
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=20,
        project_id=10,
        title="Example survey",
        visibility="link_only",
        public_slug=None,
        default_response_store_id=30,
        published_version_id=40,
        created_by_user_id=None,
        created_at=now,
        updated_at=now,
    )


def _version() -> SimpleNamespace:
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=40,
        survey_id=20,
        version_number=1,
        status="published",
        compiled_schema={"nodes": []},
        published_at=now,
        created_by_user_id=None,
        created_at=now,
        updated_at=now,
    )


def test_resume_matches_consumed_link_without_revalidating_link_state() -> None:
    link_id = UUID("00000000-0000-0000-0000-000000000001")
    session = SimpleNamespace(
        project_id=10,
        survey_id=20,
        survey_version_id=40,
        link_id=link_id,
        session_status="in_progress",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    link = SimpleNamespace(id=link_id, used_at=datetime.now(UTC), is_active=True)
    db = MagicMock()
    db.get.return_value = _version()
    payload = StartSubmissionSessionRequest.model_validate({"access": {"type": "link_token", "token": "consumed-link"}})

    with (
        patch(
            "app.services.public_submissions.api.session_management.load_current_session_record",
            return_value=session,
        ),
        patch(
            "app.services.public_submissions.api.session_management.plr.resolve_token",
            return_value=link,
        ),
        patch(
            "app.services.public_submissions.api.session_management.sr.get_survey",
            return_value=_survey(),
        ),
    ):
        response = SessionManagementService().resume_session(
            db,
            payload=payload,
            raw_resume_token="browser-session-token",
        )

    assert response.status == "in_progress"
    assert response.survey.id == 20
    assert response.published_version.id == 40


def test_resume_rejects_cookie_from_another_link() -> None:
    session = SimpleNamespace(
        project_id=10,
        survey_id=20,
        survey_version_id=40,
        link_id=UUID("00000000-0000-0000-0000-000000000001"),
        session_status="in_progress",
    )
    payload = StartSubmissionSessionRequest.model_validate({"access": {"type": "link_token", "token": "another-link"}})

    with (
        patch(
            "app.services.public_submissions.api.session_management.load_current_session_record",
            return_value=session,
        ),
        patch(
            "app.services.public_submissions.api.session_management.plr.resolve_token",
            return_value=SimpleNamespace(id=UUID("00000000-0000-0000-0000-000000000002")),
        ),
        pytest.raises(SessionNotFoundError),
    ):
        SessionManagementService().resume_session(
            MagicMock(),
            payload=payload,
            raw_resume_token="browser-session-token",
        )
