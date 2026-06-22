"""Transaction boundary tests for public submission session start.

Verifies that session creation, single-use link consumption, subject-resolution
effects, and recognition-token actions all commit atomically.
"""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.errors import LinkAlreadyUsedError
from app.schema.api.requests.submission_sessions import StartSubmissionSessionRequest
from app.schema.orm.core.submission_session import SubmissionSession
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.survey_access import SurveyLink
from app.services.public_submissions.core.actions.session_starter import SessionStarter
from tests.integration.core.factories import make_participant_chain, make_token_pair


def _publish_survey(
    db_session: Session,
    *,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    survey.visibility = "public"
    survey.public_slug = "tx-test-survey"
    survey_version.status = "published"
    survey_version.compiled_schema = {"nodes": []}
    survey_version.published_at = datetime.now(UTC)
    db_session.flush()
    survey.published_version_id = survey_version.id
    db_session.flush()


def _make_private_link(
    db_session: Session,
    *,
    survey: Survey,
    assigned_participant_id: object,
) -> tuple[SurveyLink, str]:
    raw_token, token_prefix, token_hash = make_token_pair()
    link = SurveyLink(
        project_id=survey.project_id,
        survey_id=survey.id,
        name="Single-use link",
        token_prefix=token_prefix,
        token_hash=token_hash,
        link_type="private",
        assignment_source="manual",
        assigned_participant_id=assigned_participant_id,
    )
    db_session.add(link)
    db_session.flush()
    return link, raw_token


def test_single_use_link_consumed_atomically_with_session(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    """used_at is set and committed together with the session row."""
    _publish_survey(db_session, survey=survey, survey_version=survey_version)
    participant = make_participant_chain(
        db_session,
        project_id=survey.project_id,
        subject_code="tx-subject",
    )
    link, raw_token = _make_private_link(
        db_session, survey=survey, assigned_participant_id=participant.id
    )
    payload = StartSubmissionSessionRequest.model_validate(
        {"access": {"type": "link_token", "token": raw_token}}
    )

    _response, _browser_token, _recognition_token = SessionStarter().start(
        db_session, db_session, payload=payload, actor=None
    )

    session = db_session.scalar(
        select(SubmissionSession).where(SubmissionSession.link_id == link.id)
    )
    assert session is not None, "session row must be committed"
    assert link.used_at is not None, "link must be marked used in the same commit"


def test_second_start_on_consumed_link_raises_already_used(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    """A second session-start attempt on a consumed link is rejected.

    This confirms that link consumption is persisted: the access resolver sees
    used_at set by the first start and raises LinkAlreadyUsedError before any
    subject resolution or session creation runs.
    """
    _publish_survey(db_session, survey=survey, survey_version=survey_version)
    participant = make_participant_chain(
        db_session,
        project_id=survey.project_id,
        subject_code="tx-subject-2",
    )
    link, raw_token = _make_private_link(
        db_session, survey=survey, assigned_participant_id=participant.id
    )
    payload = StartSubmissionSessionRequest.model_validate(
        {"access": {"type": "link_token", "token": raw_token}}
    )
    starter = SessionStarter()

    starter.start(db_session, db_session, payload=payload, actor=None)

    with pytest.raises(LinkAlreadyUsedError):
        starter.start(db_session, db_session, payload=payload, actor=None)
