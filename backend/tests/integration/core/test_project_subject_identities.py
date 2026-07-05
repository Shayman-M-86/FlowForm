from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.repositories.core import project_subject_identities
from app.schema.orm.core.project import Project
from app.schema.orm.core.project_subject import ProjectSubject
from app.schema.orm.core.user import User


def _make_subject(db: Session, *, project: Project) -> ProjectSubject:
    subject = ProjectSubject(project_id=project.id, subject_code="subject-1")
    db.add(subject)
    db.flush()
    return subject


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
