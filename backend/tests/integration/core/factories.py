from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy.orm import Session

from app.schema.orm.core.audit_log import AuditLog
from app.schema.orm.core.project import Project, ProjectRole
from app.schema.orm.core.project_participant import ProjectParticipant
from app.schema.orm.core.project_subject import ProjectSubject, ProjectSubjectIdentity
from app.schema.orm.core.response_store import ResponseStore
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.survey_access import SurveyPublicLink, SurveyRole
from app.schema.orm.core.user import User
from tests.survey_document import make_definition


def make_token() -> str:
    return secrets.token_urlsafe(32)


def make_user(
    auth0_user_id: str = "auth0|u1",
    email: str = "u1@example.com",
    display_name: str | None = "U1",
) -> User:
    user = User()
    user.auth0_user_id = auth0_user_id
    user.email = email
    user.display_name = display_name
    return user


def make_project(user_id: int, name: str = "Test Project", slug: str = "test-project") -> Project:
    project = Project()
    project.name = name
    project.slug = slug
    project.created_by_user_id = user_id
    return project


def make_project_role(
    project_id: int,
    name: str = "admin",
    is_system_role: bool = True,
    description: str | None = None,
) -> ProjectRole:
    role = ProjectRole()
    role.project_id = project_id
    role.name = name
    role.is_system_role = is_system_role
    role.description = description
    return role


def make_response_store(project_id: int, user_id: int, name: str = "main-store") -> ResponseStore:
    store = ResponseStore()
    store.project_id = project_id
    store.name = name
    store.store_type = "platform_postgres"
    store.connection_reference = {"kind": "postgres"}
    store.created_by_user_id = user_id
    return store


def make_survey(project_id: int, response_store_id: int, user_id: int, title: str = "Customer Survey") -> Survey:
    survey = Survey()
    survey.project_id = project_id
    survey.title = title
    survey.default_response_store_id = response_store_id
    survey.created_by_user_id = user_id
    return survey


SurveyVersionStatus = Literal["draft", "published", "archived"]


def make_survey_version(
    survey_id: int,
    user_id: int,
    version_number: int = 1,
    status: SurveyVersionStatus = "draft",
) -> SurveyVersion:
    version = SurveyVersion()
    version.survey_id = survey_id
    version.version_number = version_number
    version.definition = make_definition()
    version.revision = 0
    version.status = status
    version.created_by_user_id = user_id
    return version


def make_survey_public_link(project_id: int, survey_id: int, name: str = "test link") -> SurveyPublicLink:
    link = SurveyPublicLink()
    link.project_id = project_id
    link.survey_id = survey_id
    link.name = name
    link.token = make_token()
    link.assignment_source = "manual"
    return link


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
    subject = ProjectSubject(project_id=project_id, subject_code=subject_code)
    db_session.add(subject)
    db_session.flush()

    if user_id is not None:
        identity = ProjectSubjectIdentity(
            project_id=project_id,
            project_subject_id=subject.id,
            identity_type="authenticated_user",
            user_id=user_id,
            normalized_email=normalized_email,
            verification_status="verified",
            verified_at=datetime.now(UTC),
        )
    else:
        identity = ProjectSubjectIdentity(
            project_id=project_id,
            project_subject_id=subject.id,
            identity_type="email",
            normalized_email=normalized_email,
        )
    db_session.add(identity)
    db_session.flush()

    participant = ProjectParticipant(
        project_id=project_id,
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
    role = SurveyRole()
    role.project_id = project_id
    role.name = name
    role.description = description
    return role


def make_audit_log(
    action: str = "created",
    entity_type: str = "survey",
    entity_id: int | None = None,
    user_id: int | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    log = AuditLog()
    log.action = action
    log.entity_type = entity_type
    log.entity_id = entity_id
    log.user_id = user_id
    if metadata is not None:
        log.log_metadata = metadata
    return log
