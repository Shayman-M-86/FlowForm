from __future__ import annotations

import hashlib
import secrets

from app.models.core.project import Project, ProjectRole
from app.models.core.response_store import ResponseStore
from app.models.core.survey import Survey, SurveyVersion
from app.models.core.user import User


def make_token_pair() -> tuple[str, str, str]:
    token = secrets.token_urlsafe(32)
    token_prefix = token[:8]
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, token_prefix, token_hash


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


def make_project_role(project_id: int, name: str = "admin", is_system_role: bool = True) -> ProjectRole:
    role = ProjectRole()
    role.project_id = project_id
    role.name = name
    role.is_system_role = is_system_role
    return role


def make_response_store(project_id: int, user_id: int, name: str = "main-store") -> ResponseStore:
    store = ResponseStore()
    store.project_id = project_id
    store.name = name
    store.store_type = "platform_postgres"
    store.connection_reference = {"kind": "postgres"}
    store.created_by_user_id = user_id
    return store


def make_survey(
    project_id: int, response_store_id: int, user_id: int, title: str = "Customer Survey"
) -> Survey:
    survey = Survey()
    survey.project_id = project_id
    survey.title = title
    survey.default_response_store_id = response_store_id
    survey.created_by_user_id = user_id
    return survey


def make_survey_version(
    survey_id: int, user_id: int, version_number: int = 1, status: str = "draft"
) -> SurveyVersion:
    version = SurveyVersion()
    version.survey_id = survey_id
    version.version_number = version_number
    version.status = status
    version.created_by_user_id = user_id
    return version
