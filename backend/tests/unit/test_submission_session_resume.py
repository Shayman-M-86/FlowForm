"""A browser's previous session must only gate its own survey entry."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.domain.errors import SessionExpiredError, SessionInvalidError, SessionNotFoundError
from app.schema.api.requests.submission_sessions import StartSubmissionSessionRequest
from app.schema.orm.core.submission_session import SubmissionSession
from app.services.public_submissions.api import session_management as module


@pytest.mark.parametrize("entry_type", ["link_token", "public_slug"])
@pytest.mark.parametrize("session_state", ["completed", "abandoned", "expired", "in_progress"])
@pytest.mark.parametrize("matching_entry", [False, True])
def test_resume_session_scopes_status_to_requested_entry(
    monkeypatch: pytest.MonkeyPatch,
    entry_type: str,
    session_state: str,
    matching_entry: bool,
) -> None:
    link_id = uuid4() if entry_type == "link_token" else None
    session = SubmissionSession(
        project_id=1,
        survey_id=2,
        survey_version_id=3,
        link_id=link_id,
        session_status="in_progress" if session_state == "expired" else session_state,
        expires_at=datetime.now(UTC) + timedelta(days=-1 if session_state == "expired" else 1),
    )
    monkeypatch.setattr(module.ssr, "get_by_token_hash", lambda *_args: session)
    monkeypatch.setattr(
        module.plr,
        "resolve_token",
        lambda *_args: SimpleNamespace(id=link_id if matching_entry else uuid4()),
    )
    survey = SimpleNamespace(id=2, public_slug="previous-survey")
    monkeypatch.setattr(module.sr, "get_survey", lambda *_args, **_kwargs: survey)
    version = SimpleNamespace(survey_id=2)
    db = Mock(spec=Session)
    db.get.return_value = version
    monkeypatch.setattr(module.SurveyResponses, "model_validate", lambda _survey: "survey")
    monkeypatch.setattr(module.SurveyVersionResponses, "model_validate", lambda _version: "version")
    monkeypatch.setattr(module, "ResumeSubmissionSessionResponse", lambda **kwargs: SimpleNamespace(**kwargs))

    access = (
        {"type": "link_token", "token": "requested-link"}
        if entry_type == "link_token"
        else {"type": "public_slug", "public_slug": "previous-survey" if matching_entry else "new-survey"}
    )
    payload = StartSubmissionSessionRequest.model_validate({"access": access})
    service = module.SessionManagementService()

    if not matching_entry:
        expected_error = SessionNotFoundError
    elif session_state == "expired":
        expected_error = SessionExpiredError
    elif session_state in {"completed", "abandoned"}:
        expected_error = SessionInvalidError
    else:
        result = service.resume_session(db, payload=payload, raw_resume_token="browser-cookie")
        assert result.status == "in_progress"
        return

    with pytest.raises(expected_error):
        service.resume_session(db, payload=payload, raw_resume_token="browser-cookie")
    db.get.assert_not_called()
