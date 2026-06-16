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

    # The authenticated public-slug start resolves a subject, so both the
    # session cookie and the returning-browser recognition cookie are set.
    cookies = resp.headers.getlist("Set-Cookie")
    assert len(cookies) == 2

    session_cookie = next(c for c in cookies if "flowform_submission_session=" in c)
    assert "HttpOnly" in session_cookie
    assert "Secure" in session_cookie
    assert "SameSite=Lax" in session_cookie
    assert "Path=/api/v1/public/submission-session" in session_cookie

    recognition_cookie = next(c for c in cookies if "flowform_subject_recognition=" in c)
    assert "HttpOnly" in recognition_cookie
    assert "Secure" in recognition_cookie
    assert "SameSite=Lax" in recognition_cookie
    assert "Path=/api/v1/public" in recognition_cookie

    saved = core_db_session.scalar(select(SubmissionSession).where(SubmissionSession.survey_id == seed.survey.id))
    assert saved is not None
