from __future__ import annotations

import pytest
from flask.testing import FlaskClient
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.api.v1.respondent.submission_sessions as submission_session_routes
from app.domain.errors import SessionStartError
from app.schema.orm.core.project_subject import ProjectSubjectIdentity
from app.schema.orm.core.submission_session import SubmissionSession
from tests.e2e.conftest import SeedData


def test_start_submission_session_returns_json_tuple_and_sets_cookie(
    authed_client: FlaskClient,
    core_db_session: Session,
    seed: SeedData,
) -> None:
    resp = authed_client.post(
        "/api/v1/respondent/submission-sessions",
        json={"access": {"type": "public_slug", "public_slug": seed.survey.public_slug}},
    )

    assert resp.status_code == 201
    body = resp.get_json()
    assert set(body) == {"status", "started_at", "expires_at", "survey_version_id", "subject_code"}
    assert body["status"] == "in_progress"
    assert body["survey_version_id"] == seed.published_version.id
    assert "survey_schema" not in body
    assert "survey" not in body
    assert "version" not in body
    assert "answers" not in body

    cookies = resp.headers.getlist("Set-Cookie")
    assert len(cookies) == 2

    session_cookie = next(c for c in cookies if "flowform_submission_session=" in c)
    assert "HttpOnly" in session_cookie
    assert "Secure" in session_cookie
    assert "SameSite=Lax" in session_cookie
    assert "Path=/api/v1/respondent/submission-sessions" in session_cookie

    recognition_cookie = next(c for c in cookies if "flowform_subject_recognition=" in c)
    assert "HttpOnly" in recognition_cookie
    assert "Secure" in recognition_cookie
    assert "SameSite=Lax" in recognition_cookie
    assert "Path=/api/v1/respondent" in recognition_cookie

    saved = core_db_session.scalar(select(SubmissionSession).where(SubmissionSession.survey_id == seed.survey.id))
    assert saved is not None

    # Authenticated public-slug path (row 3) must create an identity-linked subject,
    # not a new anonymous one. This distinguishes row 3 from row 1 (anonymous).
    identity = core_db_session.scalar(
        select(ProjectSubjectIdentity).where(ProjectSubjectIdentity.project_subject_id == saved.project_subject_id)
    )
    assert identity is not None, "authenticated path must create an identity-linked subject"


def test_start_submission_session_failure_does_not_set_session_cookies(
    authed_client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
    seed: SeedData,
) -> None:
    def _fail_start_session(*args, **kwargs):
        raise SessionStartError("Core commit failed after response envelope creation")

    monkeypatch.setattr(
        submission_session_routes.session_management_service,
        "start_session",
        _fail_start_session,
    )

    resp = authed_client.post(
        "/api/v1/respondent/submission-sessions",
        json={"access": {"type": "public_slug", "public_slug": seed.survey.public_slug}},
    )

    assert resp.status_code == 500
    assert resp.headers.getlist("Set-Cookie") == []
