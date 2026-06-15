from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.repositories.core.submission_sessions import hash_browser_session_token
from app.schema.api.requests.submission_sessions import StartSubmissionSessionRequest
from app.schema.orm.core.submission_session import SubmissionSession
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.survey_access import SurveyLink
from app.schema.orm.core.user import User
from app.services.submissions.session_starter import SessionStarter
from tests.integration.core.factories import make_participant_chain, make_token_pair


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


def test_start_public_slug_session_creates_anonymous_core_session(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    _publish_public_survey(db_session, survey=survey, survey_version=survey_version)
    payload = StartSubmissionSessionRequest.model_validate(
        {"access": {"type": "public_slug", "public_slug": "customer-intake"}}
    )

    response, raw_browser_session_token = SessionStarter().start(db_session, payload=payload, actor=None)

    saved = db_session.scalar(select(SubmissionSession).where(SubmissionSession.survey_id == survey.id))
    assert saved is not None
    assert response.status == "in_progress"
    assert response.survey_version_id == survey_version.id
    assert saved.project_id == survey.project_id
    assert saved.survey_id == survey.id
    assert saved.survey_version_id == survey_version.id
    assert saved.response_store_id == survey.default_response_store_id
    assert saved.link_id is None
    # V1 policy: anonymous public sessions do not create project_subjects rows.
    assert saved.project_subject_id is None
    assert saved.browser_session_token_hash == hash_browser_session_token(raw_browser_session_token)
    assert saved.expires_at > saved.started_at


def test_start_assigned_link_session_uses_server_owned_subject(
    db_session: Session,
    user: User,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    _publish_public_survey(db_session, survey=survey, survey_version=survey_version)
    participant = make_participant_chain(db_session, project_id=survey.project_id, subject_code="assigned-subject")

    raw_token, token_prefix, token_hash = make_token_pair()
    link = SurveyLink(
        project_id=survey.project_id,
        survey_id=survey.id,
        name="Assigned respondent",
        token_prefix=token_prefix,
        token_hash=token_hash,
        link_type="private",
        assignment_source="manual",
        assigned_participant_id=participant.id,
    )
    db_session.add(link)
    db_session.flush()
    payload = StartSubmissionSessionRequest.model_validate({"access": {"type": "link_token", "token": raw_token}})

    response, _raw_browser_session_token = SessionStarter().start(db_session, payload=payload, actor=user)

    saved = db_session.scalar(select(SubmissionSession).where(SubmissionSession.link_id == link.id))
    assert saved is not None
    assert response.survey_version_id == survey_version.id
    assert saved.link_id == link.id
    assert saved.project_subject_id == participant.project_subject_id
    assert link.used_at is not None


def test_start_unassigned_reusable_link_session_does_not_stamp_used_at(
    db_session: Session,
    survey: Survey,
    survey_version: SurveyVersion,
) -> None:
    _publish_public_survey(db_session, survey=survey, survey_version=survey_version)
    raw_token, token_prefix, token_hash = make_token_pair()
    link = SurveyLink(
        project_id=survey.project_id,
        survey_id=survey.id,
        name="Reusable anonymous link",
        token_prefix=token_prefix,
        token_hash=token_hash,
        assignment_source="manual",
    )
    db_session.add(link)
    db_session.flush()
    payload = StartSubmissionSessionRequest.model_validate({"access": {"type": "link_token", "token": raw_token}})

    response, _raw_browser_session_token = SessionStarter().start(db_session, payload=payload, actor=None)

    saved = db_session.scalar(select(SubmissionSession).where(SubmissionSession.link_id == link.id))
    assert saved is not None
    assert response.survey_version_id == survey_version.id
    assert saved.link_id == link.id
    assert saved.project_subject_id is None
    # A reusable link with no assignment must not be stamped used_at; the DB
    # CHECK ck_survey_links_used_at_requires_assignment forbids used_at without
    # an assignment, and the link must remain reusable.
    assert link.used_at is None
