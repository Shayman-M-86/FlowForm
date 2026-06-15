from __future__ import annotations

from flask.testing import FlaskClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schema.orm.core.submission_session import SubmissionSession
from tests.e2e.conftest import SeedData


def test_start_submission_session_returns_json_tuple_and_sets_cookie(
    authed_client: FlaskClient,
    core_db_session: Session,
    seed: SeedData,
) -> None:
    resp = authed_client.post(
        "/api/v1/public/submission-session/start",
        json={"access": {"type": "public_slug", "public_slug": seed.survey.public_slug}},
    )

    assert resp.status_code == 201
    body = resp.get_json()
    assert set(body) == {"status", "started_at", "expires_at", "survey_version_id"}
    assert body["status"] == "in_progress"
    assert body["survey_version_id"] == seed.published_version.id
    assert "survey" not in body
    assert "version" not in body
    assert "answers" not in body

    cookies = resp.headers.getlist("Set-Cookie")
    assert len(cookies) == 1
    assert "flowform_submission_session=" in cookies[0]
    assert "HttpOnly" in cookies[0]
    assert "Secure" in cookies[0]
    assert "SameSite=Lax" in cookies[0]
    assert "Path=/api/v1/public/submission-session" in cookies[0]

    saved = core_db_session.scalar(select(SubmissionSession).where(SubmissionSession.survey_id == seed.survey.id))
    assert saved is not None
