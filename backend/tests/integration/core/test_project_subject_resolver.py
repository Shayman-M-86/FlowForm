from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.repositories.core import project_subject_tokens
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
from tests.integration.core.factories import make_token_pair


def _make_subject(
    db_session: Session, *, project: Project, subject_code: str = "subject-1"
) -> ProjectSubject:
    subject = ProjectSubject(project_id=project.id, subject_code=subject_code)
    db_session.add(subject)
    db_session.flush()
    return subject


def test_resolve_prefers_link_assigned_subject(
    db_session: Session,
    project: Project,
    survey: Survey,
) -> None:
    subject = _make_subject(db_session, project=project)
    _, token_prefix, token_hash = make_token_pair()
    link = SurveyLink(
        project_id=project.id,
        survey_id=survey.id,
        name="Assigned link",
        token_prefix=token_prefix,
        token_hash=token_hash,
        assigned_subject_id=subject.id,
    )
    db_session.add(link)
    db_session.flush()

    resolved = ProjectSubjectResolver().resolve(
        db_session,
        project_id=project.id,
        link=link,
        actor=None,
    )

    assert resolved is not None
    assert resolved.id == subject.id


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

    assert resolved is not None
    assert resolved.id == subject.id


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

    assert resolved is None


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

    assert resolved is not None
    assert resolved.id == subject.id
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

    assert resolved is None


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

    assert resolved is None


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

    assert resolved is not None
    assert resolved.project_id == project.id
    persisted = db_session.scalar(select(ProjectSubject).where(ProjectSubject.id == resolved.id))
    assert persisted is not None
