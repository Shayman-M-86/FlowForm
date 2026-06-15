from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.repositories.core import project_subject_identities, project_subject_tokens
from app.schema.orm.core.project import Project
from app.schema.orm.core.project_subject import (
    ProjectSubject,
    ProjectSubjectIdentity,
    ProjectSubjectToken,
)
from app.schema.orm.core.survey import Survey
from app.schema.orm.core.survey_access import SurveyLink
from app.schema.orm.core.user import User
from app.services.submissions.project_subject_resolver import ProjectSubjectResolver
from tests.integration.core.factories import make_participant_chain, make_token_pair


def _make_subject(
    db_session: Session, *, project: Project, subject_code: str = "subject-1"
) -> ProjectSubject:
    subject = ProjectSubject(project_id=project.id, subject_code=subject_code)
    db_session.add(subject)
    db_session.flush()
    return subject


def test_resolve_prefers_link_assigned_participant(
    db_session: Session,
    project: Project,
    survey: Survey,
) -> None:
    participant = make_participant_chain(db_session, project_id=project.id, subject_code="subject-1")
    _, token_prefix, token_hash = make_token_pair()
    link = SurveyLink(
        project_id=project.id,
        survey_id=survey.id,
        name="Assigned link",
        token_prefix=token_prefix,
        token_hash=token_hash,
        link_type="private",
        assignment_source="manual",
        assigned_participant_id=participant.id,
    )
    db_session.add(link)
    db_session.flush()

    resolved = ProjectSubjectResolver().resolve(
        db_session,
        project_id=project.id,
        link=link,
        actor=None,
    )

    assert resolved.source == "assigned_link"
    assert resolved.subject is not None
    assert resolved.subject.id == participant.project_subject_id


def test_resolve_uses_actor_active_user_identity(
    db_session: Session,
    project: Project,
    user: User,
) -> None:
    subject = _make_subject(db_session, project=project)
    identity = ProjectSubjectIdentity(
        project_id=project.id,
        project_subject_id=subject.id,
        identity_type="authenticated_user",
        user_id=user.id,
        normalized_email=user.email,
        verification_status="verified",
        verified_at=datetime.now(UTC),
    )
    db_session.add(identity)
    db_session.flush()

    resolved = ProjectSubjectResolver().resolve(
        db_session,
        project_id=project.id,
        link=None,
        actor=user,
    )

    assert resolved.source == "authenticated_user"
    assert resolved.subject is not None
    assert resolved.subject.id == subject.id


def test_create_user_identity_sets_verified_email_fields(
    db_session: Session,
    project: Project,
    user: User,
) -> None:
    subject = _make_subject(db_session, project=project)
    current = datetime.now(UTC)

    identity = project_subject_identities.create_user_identity(
        db_session,
        project_id=project.id,
        project_subject_id=subject.id,
        user=user,
        now=current,
    )

    assert identity.identity_type == "authenticated_user"
    assert identity.user_id == user.id
    assert identity.normalized_email == user.email.strip().lower()
    assert identity.verification_status == "verified"
    assert identity.verified_at == current
    assert identity.attached_at == current


def test_resolve_ignores_actor_without_identity(
    db_session: Session,
    project: Project,
    user: User,
) -> None:
    resolved = ProjectSubjectResolver().resolve(
        db_session,
        project_id=project.id,
        link=None,
        actor=user,
    )

    assert resolved.source == "none"
    assert resolved.subject is None


def test_resolve_uses_recognition_token_and_marks_used(
    db_session: Session,
    project: Project,
) -> None:
    subject = _make_subject(db_session, project=project)
    raw_token = "recognition-token-value"
    token = ProjectSubjectToken(
        project_id=project.id,
        project_subject_id=subject.id,
        token_hash=project_subject_tokens.hash_recognition_token(raw_token),
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    db_session.add(token)
    db_session.flush()

    resolved = ProjectSubjectResolver().resolve(
        db_session,
        project_id=project.id,
        link=None,
        actor=None,
        recognition_token=raw_token,
    )

    assert resolved.source == "recognition_token"
    assert resolved.subject is not None
    assert resolved.subject.id == subject.id
    assert token.last_used_at is not None


def test_resolve_ignores_revoked_recognition_token(
    db_session: Session,
    project: Project,
) -> None:
    subject = _make_subject(db_session, project=project)
    raw_token = "revoked-token"
    token = ProjectSubjectToken(
        project_id=project.id,
        project_subject_id=subject.id,
        token_hash=project_subject_tokens.hash_recognition_token(raw_token),
        expires_at=datetime.now(UTC) + timedelta(days=30),
        revoked_at=datetime.now(UTC),
    )
    db_session.add(token)
    db_session.flush()

    resolved = ProjectSubjectResolver().resolve(
        db_session,
        project_id=project.id,
        link=None,
        actor=None,
        recognition_token=raw_token,
    )

    assert resolved.source == "none"
    assert resolved.subject is None


def test_resolve_returns_none_when_no_context_matches(
    db_session: Session,
    project: Project,
) -> None:
    resolved = ProjectSubjectResolver().resolve(
        db_session,
        project_id=project.id,
        link=None,
        actor=None,
    )

    assert resolved.source == "none"
    assert resolved.subject is None


def test_resolve_creates_anonymous_subject_when_requested(
    db_session: Session,
    project: Project,
) -> None:
    resolved = ProjectSubjectResolver().resolve(
        db_session,
        project_id=project.id,
        link=None,
        actor=None,
        create_anonymous_subject=True,
    )

    assert resolved.source == "anonymous_created"
    assert resolved.subject is not None
    assert resolved.subject.project_id == project.id
    persisted = db_session.scalar(select(ProjectSubject).where(ProjectSubject.id == resolved.subject.id))
    assert persisted is not None
