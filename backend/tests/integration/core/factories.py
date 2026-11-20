from __future__ import annotations

import secrets
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from app.schema.enums import SurveyVersionStatus
from app.schema.models.survey_document.document import SurveyContent
from app.schema.orm.core.audit_log import AuditLog
from app.schema.orm.core.project import Project, ProjectRole
from app.schema.orm.core.project_participant import ProjectParticipant
from app.schema.orm.core.project_subject import ProjectSubject, ProjectSubjectIdentity
from app.schema.orm.core.response_store import ResponseStore
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.survey_access import SurveyRole
from app.schema.orm.core.user import User
from app.schema.types import Auth0UserId, ProjectId, ResponseStoreId, SurveyId, UserId


def make_token() -> str:
    return secrets.token_urlsafe(32)


def make_user(
    auth0_user_id: str = "auth0|u1",
    email: str = "u1@example.com",
    display_name: str | None = "U1",
) -> User:
    user = User(
        auth0_user_id=TypeAdapter(Auth0UserId).validate_python(auth0_user_id),
        email=email,
    )
    user.display_name = display_name
    return user


def make_project(user_id: int | None, name: str = "Test Project", slug: str = "test-project") -> Project:
    project = Project(
        name=name,
        slug=slug,
    )
    project.created_by_user_id = TypeAdapter(UserId | None).validate_python(user_id)
    return project


def make_project_role(
    project_id: int,
    name: str = "admin",
    is_system_role: bool = True,
    description: str | None = None,
) -> ProjectRole:
    role = ProjectRole(
        project_id=TypeAdapter(ProjectId).validate_python(project_id),
        name=name,
    )
    role.is_system_role = is_system_role
    role.description = description
    return role


def make_response_store(project_id: int, user_id: int | None, name: str = "main-store") -> ResponseStore:
    store = ResponseStore(
        project_id=TypeAdapter(ProjectId).validate_python(project_id),
        name=name,
        store_type="platform_postgres",
        connection_reference={"kind": "postgres"},
    )
    store.created_by_user_id = TypeAdapter(UserId | None).validate_python(user_id)
    return store


def make_survey(project_id: int, response_store_id: int | None, user_id: int, title: str = "Customer Survey") -> Survey:
    survey = Survey(
        project_id=TypeAdapter(ProjectId).validate_python(project_id),
        title=title,
    )
    survey.default_response_store_id = (
        TypeAdapter(ResponseStoreId).validate_python(response_store_id) if response_store_id is not None else None
    )
    survey.created_by_user_id = TypeAdapter(UserId).validate_python(user_id)
    return survey


def make_survey_version(
    survey_id: int,
    user_id: int,
    version_number: int = 1,
    status: SurveyVersionStatus = "draft",
) -> SurveyVersion:
    version = SurveyVersion(
        survey_id=TypeAdapter(SurveyId).validate_python(survey_id),
        version_number=version_number,
    )
    version.status = status
    version.created_by_user_id = TypeAdapter(UserId).validate_python(user_id)
    return version


def define_version(
    db: Session,
    version: SurveyVersion,
    *,
    field_ids: tuple[str, ...] = (),
) -> SurveyContent:
    """Attach content to a version and mark its first revision."""
    if version.id is None:
        status = version.status
        version.status = "draft"
        db.add(version)
        db.flush()
        version.status = status
    definition = SurveyContent.model_validate(
        {
            "title": "Test survey",
            "sections": [
                {
                    "id": "main",
                    "title": "Main",
                    "blocks": [
                        {
                            "id": field_id,
                            "type": "input",
                            "field": {
                                "id": field_id,
                                "uuid": uuid4(),
                                "prompt": field_id,
                                "interaction": {"kind": "short_text"},
                                "answerSpec": {"type": "string", "required": False},
                            },
                        }
                        for field_id in field_ids
                    ],
                }
            ],
        }
    )
    version.content = definition
    version.revision = 1
    return definition


def make_participant_chain(
    db_session: Session,
    *,
    project_id: int,
    subject_code: str = "subject-1",
    normalized_email: str = "participant@example.com",
    user_id: int | None = None,
) -> ProjectParticipant:
    """Create a subject + identity + participant chain for a link assignment.

    Pass `user_id` to create an `authenticated_user` identity instead of an
    `email` identity (for authenticated-link tests).
    """
    subject = ProjectSubject(project_id=TypeAdapter(ProjectId).validate_python(project_id), subject_code=subject_code)
    db_session.add(subject)
    db_session.flush()

    if user_id is not None:
        now = datetime.now(UTC)
        identity = ProjectSubjectIdentity(
            project_id=TypeAdapter(ProjectId).validate_python(project_id),
            project_subject_id=subject.id,
            identity_type="authenticated_user",
            user_id=TypeAdapter(UserId).validate_python(user_id),
            normalized_email=normalized_email,
            verification_status="verified",
            verified_at=now,
            attached_at=now,
        )
    else:
        identity = ProjectSubjectIdentity(
            project_id=TypeAdapter(ProjectId).validate_python(project_id),
            project_subject_id=subject.id,
            identity_type="email",
            normalized_email=normalized_email,
        )
    db_session.add(identity)
    db_session.flush()

    participant = ProjectParticipant(
        project_id=TypeAdapter(ProjectId).validate_python(project_id),
        project_subject_id=subject.id,
        identity_id=identity.id,
    )
    db_session.add(participant)
    db_session.flush()
    return participant


def make_survey_role(
    project_id: int,
    name: str = "reviewer",
    description: str | None = None,
) -> SurveyRole:
    role = SurveyRole(
        project_id=TypeAdapter(ProjectId).validate_python(project_id),
        name=name,
    )
    role.description = description
    return role


def make_audit_log(
    action: str = "created",
    entity_type: str = "survey",
    entity_id: int | None = None,
    user_id: int | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    log = AuditLog(
        action=action,
        entity_type=entity_type,
    )
    log.entity_id = entity_id
    log.user_id = TypeAdapter(UserId).validate_python(user_id) if user_id is not None else None
    if metadata is not None:
        log.log_metadata = metadata
    return log
