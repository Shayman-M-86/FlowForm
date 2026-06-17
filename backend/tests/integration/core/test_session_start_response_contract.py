"""Session start response contract tests.

Verifies that:
- session start does not include survey_schema (schema belongs to discovery/link-resolution)
- token delivery: browser-session and recognition tokens go to cookies, not body

Docs: 01-service-boundary.md — survey schema delivery belongs to discovery flows.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.schema.api.requests.submission_sessions import StartSubmissionSessionRequest
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.survey_access import SurveyLink
from app.services.public_submissions.core.session_starter import SessionStarter
from tests.integration.core.factories import make_participant_chain, make_token_pair

_SCHEMA = {"nodes": [{"id": "q1", "type": "short_text"}]}


def _publish_survey(
    db: Session,
    *,
    survey: Survey,
    survey_version: SurveyVersion,
    public_slug: str | None = None,
) -> None:
    if public_slug is not None:
        survey.visibility = "public"
        survey.public_slug = public_slug
    else:
        survey.visibility = "link_only"
    survey_version.status = "published"
    survey_version.compiled_schema = _SCHEMA
    survey_version.published_at = datetime.now(UTC)
    db.flush()
    survey.published_version_id = survey_version.id
    db.flush()


def _make_general_link(db: Session, *, survey: Survey) -> tuple[SurveyLink, str]:
    raw_token, token_prefix, token_hash = make_token_pair()
    link = SurveyLink(
        project_id=survey.project_id,
        survey_id=survey.id,
        name="General link",
        token_prefix=token_prefix,
        token_hash=token_hash,
        link_type="general",
        assignment_source="manual",
        assigned_participant_id=None,
    )
    db.add(link)
    db.flush()
    return link, raw_token


def _make_private_link(
    db: Session, *, survey: Survey, assigned_participant_id: object
) -> tuple[SurveyLink, str]:
    raw_token, token_prefix, token_hash = make_token_pair()
    link = SurveyLink(
        project_id=survey.project_id,
        survey_id=survey.id,
        name="Private link",
        token_prefix=token_prefix,
        token_hash=token_hash,
        link_type="private",
        assignment_source="manual",
        assigned_participant_id=assigned_participant_id,
    )
    db.add(link)
    db.flush()
    return link, raw_token


def test_public_slug_session_start_omits_survey_schema(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    """Session start must not include survey_schema — schema belongs to discovery flows."""
    _publish_survey(db_session, survey=survey, survey_version=survey_version, public_slug="schema-test-slug")
    payload = StartSubmissionSessionRequest.model_validate(
        {"access": {"type": "public_slug", "public_slug": "schema-test-slug"}}
    )

    response, _browser_token, _recognition_token = SessionStarter().start(
        db_session, db_session, payload=payload, actor=None
    )

    assert not hasattr(response, "survey_schema"), "session start must not include survey_schema"


def test_general_link_session_start_omits_survey_schema(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    """Session start must not include survey_schema — schema belongs to discovery flows."""
    _publish_survey(db_session, survey=survey, survey_version=survey_version)
    _link, raw_token = _make_general_link(db_session, survey=survey)
    payload = StartSubmissionSessionRequest.model_validate(
        {"access": {"type": "link_token", "token": raw_token}}
    )

    response, _browser_token, _recognition_token = SessionStarter().start(
        db_session, db_session, payload=payload, actor=None
    )

    assert not hasattr(response, "survey_schema"), "session start must not include survey_schema"


def test_private_link_session_start_omits_survey_schema(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    """Session start must not include survey_schema — schema belongs to discovery flows."""
    _publish_survey(db_session, survey=survey, survey_version=survey_version)
    participant = make_participant_chain(
        db_session, project_id=survey.project_id, subject_code="schema-test-assigned"
    )
    _link, raw_token = _make_private_link(
        db_session, survey=survey, assigned_participant_id=participant.id
    )
    payload = StartSubmissionSessionRequest.model_validate(
        {"access": {"type": "link_token", "token": raw_token}}
    )

    response, _browser_token, _recognition_token = SessionStarter().start(
        db_session, db_session, payload=payload, actor=None
    )

    assert not hasattr(response, "survey_schema"), "session start must not include survey_schema"


def test_public_slug_session_start_returns_browser_session_token(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    """Session start must return a non-empty browser session token for the cookie."""
    _publish_survey(db_session, survey=survey, survey_version=survey_version, public_slug="cookie-test-slug")
    payload = StartSubmissionSessionRequest.model_validate(
        {"access": {"type": "public_slug", "public_slug": "cookie-test-slug"}}
    )

    _response, browser_token, _recognition_token = SessionStarter().start(
        db_session, db_session, payload=payload, actor=None
    )

    assert browser_token, "browser session token must be non-empty"


def test_public_slug_session_start_returns_recognition_token_for_new_subject(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    """Session start for a new anonymous subject must issue and return a recognition token."""
    _publish_survey(db_session, survey=survey, survey_version=survey_version, public_slug="recog-test-slug")
    payload = StartSubmissionSessionRequest.model_validate(
        {"access": {"type": "public_slug", "public_slug": "recog-test-slug"}}
    )

    _response, _browser_token, recognition_token = SessionStarter().start(
        db_session, db_session, payload=payload, actor=None
    )

    assert recognition_token is not None, "a new anonymous subject must receive a recognition token"
