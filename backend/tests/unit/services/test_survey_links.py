from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.survey_links import SurveyLinkService


def _email_link() -> SimpleNamespace:
    identity = SimpleNamespace(normalized_email="respondent@example.com")
    participant = SimpleNamespace(identity=identity)
    return SimpleNamespace(
        assigned_participant=participant,
        expires_at=None,
        token="survey-token",
        emailed_at=None,
    )


def _settings() -> SimpleNamespace:
    return SimpleNamespace(flowform=SimpleNamespace(server=SimpleNamespace(site_url="https://flowform.example")))


def test_disabled_email_delivery_does_not_record_sent_timestamp() -> None:
    service = SurveyLinkService()
    db = MagicMock()
    survey = SimpleNamespace(title="Example survey")
    link = _email_link()
    email_service = MagicMock()
    email_service.send_survey_invite.return_value = None

    with (
        patch.object(
            service,
            "_ensure_survey_and_public_id_match",
            return_value=survey,
        ),
        patch.object(
            service,
            "_get_link_invalidate",
            return_value=link,
        ),
        patch(
            "app.services.survey_links.get_email_service",
            return_value=email_service,
        ),
        patch(
            "app.services.survey_links.current_settings",
            return_value=_settings(),
        ),
        patch("app.services.survey_links.commit_with_err_handle") as commit,
    ):
        message_id = service.send_link_email(
            db,
            survey_id=20,
            project_id=10,
            link_id=MagicMock(),
            actor=MagicMock(),
        )

    assert message_id is None
    assert link.emailed_at is None
    commit.assert_not_called()


def test_successful_email_delivery_records_sent_timestamp() -> None:
    service = SurveyLinkService()
    db = MagicMock()
    survey = SimpleNamespace(title="Example survey")
    link = _email_link()
    email_service = MagicMock()
    email_service.send_survey_invite.return_value = "message-123"

    with (
        patch.object(
            service,
            "_ensure_survey_and_public_id_match",
            return_value=survey,
        ),
        patch.object(
            service,
            "_get_link_invalidate",
            return_value=link,
        ),
        patch(
            "app.services.survey_links.get_email_service",
            return_value=email_service,
        ),
        patch(
            "app.services.survey_links.current_settings",
            return_value=_settings(),
        ),
        patch("app.services.survey_links.commit_with_err_handle") as commit,
    ):
        message_id = service.send_link_email(
            db,
            survey_id=20,
            project_id=10,
            link_id=MagicMock(),
            actor=MagicMock(),
        )

    assert message_id == "message-123"
    assert link.emailed_at is not None
    commit.assert_called_once_with(db)
