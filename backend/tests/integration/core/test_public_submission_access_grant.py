from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.schema.api.requests.submission_sessions import StartSubmissionSessionRequest
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.survey_access import SurveyLink
from app.schema.orm.core.user import User
from app.services.public_submissions.core.access_resolver import AccessResolver
from tests.integration.core.factories import make_participant_chain, make_token_pair


def _publish_survey(
    db_session: Session,
    *,
    survey: Survey,
    survey_version: SurveyVersion,
    visibility: str = "public",
    slug: str | None = "customer-intake",
) -> None:
    survey.visibility = visibility
    survey.public_slug = slug
    survey_version.status = "published"
    survey_version.compiled_schema = {"nodes": []}
    survey_version.published_at = datetime.now(UTC)
    db_session.flush()
    survey.published_version_id = survey_version.id
    db_session.flush()


def _slug_payload(slug: str) -> StartSubmissionSessionRequest:
    return StartSubmissionSessionRequest.model_validate(
        {"access": {"type": "public_slug", "public_slug": slug}}
    )


def _token_payload(token: str) -> StartSubmissionSessionRequest:
    return StartSubmissionSessionRequest.model_validate(
        {"access": {"type": "link_token", "token": token}}
    )


def _make_link(
    db_session: Session,
    *,
    survey: Survey,
    name: str,
    link_type: str = "general",
    assigned_participant_id=None,
) -> tuple[SurveyLink, str]:
    raw_token, token_prefix, token_hash = make_token_pair()
    link = SurveyLink(
        project_id=survey.project_id,
        survey_id=survey.id,
        name=name,
        token_prefix=token_prefix,
        token_hash=token_hash,
        link_type=link_type,
        assignment_source="manual",
        assigned_participant_id=assigned_participant_id,
    )
    db_session.add(link)
    db_session.flush()
    return link, raw_token


def test_public_slug_grant_carries_explicit_access_context(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    _publish_survey(db_session, survey=survey, survey_version=survey_version)

    grant = AccessResolver().resolve(
        db_session, payload=_slug_payload("customer-intake"), actor=None
    )

    assert grant.access_method == "public_slug"
    assert grant.project_id == survey.project_id
    assert grant.survey_id == survey.id
    assert grant.survey_version_id == survey_version.id
    assert grant.link_id is None
    assert grant.assigned_subject_id is None
    assert grant.requires_auth is False
    assert grant.is_single_use is False
    assert grant.survey is survey
    assert grant.published_version is survey_version
    assert grant.link is None


def test_general_link_grant_carries_reusable_link_context(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    _publish_survey(
        db_session,
        survey=survey,
        survey_version=survey_version,
        visibility="link_only",
        slug=None,
    )
    link, raw_token = _make_link(db_session, survey=survey, name="General link")

    grant = AccessResolver().resolve(
        db_session, payload=_token_payload(raw_token), actor=None
    )

    assert grant.access_method == "general_link"
    assert grant.project_id == survey.project_id
    assert grant.survey_id == survey.id
    assert grant.survey_version_id == survey_version.id
    assert grant.link_id == link.id
    assert grant.assigned_subject_id is None
    assert grant.requires_auth is False
    assert grant.is_single_use is False
    assert grant.link is link


def test_private_link_grant_carries_assigned_subject_candidate(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    _publish_survey(db_session, survey=survey, survey_version=survey_version)
    participant = make_participant_chain(
        db_session, project_id=survey.project_id, subject_code="private-subject"
    )
    link, raw_token = _make_link(
        db_session,
        survey=survey,
        name="Private link",
        link_type="private",
        assigned_participant_id=participant.id,
    )

    grant = AccessResolver().resolve(
        db_session, payload=_token_payload(raw_token), actor=None
    )

    assert grant.access_method == "private_link"
    assert grant.link_id == link.id
    assert grant.assigned_subject_id == participant.project_subject_id
    assert grant.requires_auth is False
    assert grant.is_single_use is True


def test_authenticated_link_grant_carries_auth_requirement(
    db_session: Session,
    user: User,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    _publish_survey(db_session, survey=survey, survey_version=survey_version)
    participant = make_participant_chain(
        db_session,
        project_id=survey.project_id,
        subject_code="auth-subject",
        normalized_email=user.email,
        user_id=user.id,
    )
    link, raw_token = _make_link(
        db_session,
        survey=survey,
        name="Authenticated link",
        link_type="authenticated",
        assigned_participant_id=participant.id,
    )

    grant = AccessResolver().resolve(
        db_session, payload=_token_payload(raw_token), actor=user
    )

    assert grant.access_method == "authenticated_assigned_link"
    assert grant.link_id == link.id
    assert grant.assigned_subject_id == participant.project_subject_id
    assert grant.requires_auth is True
    assert grant.is_single_use is True
