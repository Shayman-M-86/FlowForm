


from __future__ import annotations

from app.core.errors import ForbiddenError
from app.services.access.access_service import ProjectAccess, SurveyAccess


def ensure_project_member(access: ProjectAccess) -> None:
    if access.membership is None:
        raise ForbiddenError(message="You do not have access to this project")


def ensure_project_permission(access: ProjectAccess, permission: str) -> None:
    ensure_project_member(access)

    if permission not in access.permissions:
        raise ForbiddenError(message=f"Missing permission: {permission}")



def ensure_survey_member(access: SurveyAccess) -> None:
    if access.membership is None:
        raise ForbiddenError(message="You do not have access to this survey")


def ensure_survey_permission(access: SurveyAccess, permission: str) -> None:
    ensure_survey_member(access)

    if permission not in access.permissions:
        raise ForbiddenError(message=f"Missing permission: {permission}")