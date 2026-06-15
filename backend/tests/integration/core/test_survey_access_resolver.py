from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.domain.errors import (
    LinkInactiveError,
    LinkNotFoundError,
    SurveyNotFoundBySlugError,
    SurveyNotPublishedError,
)
from app.schema.api.requests.submission_sessions import StartSubmissionSessionRequest
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.survey_access import SurveyLink
from app.services.submissions.access_resolver import SurveyAccessResolver
from tests.integration.core.factories import make_token_pair


def _publish_public_survey(
    db_session: Session,
    *,
    survey: Survey,
    survey_version: SurveyVersion,
    slug: str = "customer-intake",
) -> None:
    survey.visibility = "public"
    survey.public_slug = slug
    survey_version.status = "published"
    survey_version.compiled_schema = {"nodes": []}
    survey_version.published_at = datetime.now(UTC)
    db_session.flush()
    survey.published_version_id = survey_version.id
    db_session.flush()


def _slug_payload(slug: str) -> StartSubmissionSessionRequest:
    return StartSubmissionSessionRequest.model_validate({"access": {"type": "public_slug", "public_slug": slug}})


def _token_payload(token: str) -> StartSubmissionSessionRequest:
    return StartSubmissionSessionRequest.model_validate({"access": {"type": "link_token", "token": token}})


def test_resolve_public_slug_returns_published_version(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    _publish_public_survey(db_session, survey=survey, survey_version=survey_version)

    grant = SurveyAccessResolver().resolve(db_session, payload=_slug_payload("customer-intake"), actor=None)

    assert grant.survey.id == survey.id
    assert grant.published_version.id == survey_version.id
    assert grant.link is None


def test_resolve_public_slug_unknown_slug_raises(
    db_session: Session,
) -> None:
    with pytest.raises(SurveyNotFoundBySlugError):
        SurveyAccessResolver().resolve(db_session, payload=_slug_payload("no-such-slug"), actor=None)


def test_resolve_public_slug_without_published_version_raises(
    db_session: Session,
    survey: Survey,
) -> None:
    survey.visibility = "public"
    survey.public_slug = "public-no-version"
    db_session.flush()

    with pytest.raises(SurveyNotPublishedError):
        SurveyAccessResolver().resolve(db_session, payload=_slug_payload("public-no-version"), actor=None)


def test_resolve_link_token_unknown_token_raises(
    db_session: Session,
) -> None:
    with pytest.raises(LinkNotFoundError):
        SurveyAccessResolver().resolve(db_session, payload=_token_payload("unknown-token"), actor=None)


def test_resolve_link_token_inactive_link_raises(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    _publish_public_survey(db_session, survey=survey, survey_version=survey_version)
    raw_token, token_prefix, token_hash = make_token_pair()
    link = SurveyLink(
        project_id=survey.project_id,
        survey_id=survey.id,
        name="Inactive link",
        token_prefix=token_prefix,
        token_hash=token_hash,
        assignment_source="manual",
        is_active=False,
    )
    db_session.add(link)
    db_session.flush()

    with pytest.raises(LinkInactiveError):
        SurveyAccessResolver().resolve(db_session, payload=_token_payload(raw_token), actor=None)
