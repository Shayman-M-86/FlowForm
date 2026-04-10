from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import ParamSpec, TypeVar, cast

from sqlalchemy.orm import Session

from app.domain import access_rules
from app.repositories import access_repo, surveys_repo
from app.schema.orm.core import ProjectMembership, SurveyMembershipRole, User

P = ParamSpec("P")
R = TypeVar("R")


@dataclass(slots=True)
class ProjectAccess:
    """Project-scoped access data for a user.

    Represents the result of resolving a user's membership and permissions
    within a project.

    Attributes:
        membership: The user's project membership, if one exists.
        permissions: The set of permission names granted via the project role.
    """

    membership: ProjectMembership | None
    permissions: set[str]


@dataclass(slots=True)
class SurveyAccess:
    """Survey-scoped access data built on top of project access.

    Combines project-level access with any survey-specific role assignment
    to produce an effective permission set for a survey.

    Attributes:
        project_access: The resolved project-level access for the user.
        survey_membership_role: The survey-specific role assignment, if any.
        survey_permissions: Permissions granted via the survey role.
    """

    project_access: ProjectAccess
    survey_membership_role: SurveyMembershipRole | None
    survey_permissions: set[str]

    @property
    def membership(self) -> ProjectMembership | None:
        """Return the resolved project membership.

        Returns:
            The user's project membership, or None if not a member.
        """
        return self.project_access.membership

    @property
    def permissions(self) -> set[str]:
        """Return the combined effective permissions.

        Returns:
            A set containing both project-level and survey-level permissions.
        """
        return self.project_access.permissions | self.survey_permissions


class AccessService:
    """Resolve membership and permission data for project and survey access.

    This service is used by application services to determine what a user
    is allowed to do before executing business logic. It does not enforce
    permissions directly; instead, it returns access data that should be
    validated by access rules.
    """

    def get_project_access(
        self,
        db: Session,
        *,
        project_id: int,
        user_id: int,
    ) -> ProjectAccess:
        """Resolve project-level access for a user.

        Args:
            db: Database session.
            project_id: ID of the project being accessed.
            user_id: ID of the user requesting access.

        Returns:
            A ProjectAccess object containing membership and permissions.
            If the user is not a project member, membership will be None
            and permissions will be an empty set.
        """
        membership = access_repo.get_project_membership(
            db,
            project_id=project_id,
            user_id=user_id,
        )

        if membership is None:
            return ProjectAccess(membership=None, permissions=set())

        permissions = (
            {permission.name for permission in membership.role.permissions} if membership.role is not None else set()
        )

        return ProjectAccess(
            membership=membership,
            permissions=permissions,
        )

    def get_survey_access(
        self,
        db: Session,
        *,
        project_id: int,
        survey_id: int,
        user_id: int,
    ) -> SurveyAccess:
        """Resolve project and survey-level access for a user.

        Args:
            db: Database session.
            project_id: ID of the project containing the survey.
            survey_id: ID of the survey being accessed.
            user_id: ID of the user requesting access.

        Returns:
            A SurveyAccess object combining project-level and survey-level
            permissions. If the user is not a member of the project or the
            survey does not exist, survey-level permissions will be empty.
        """
        project_access = self.get_project_access(
            db,
            project_id=project_id,
            user_id=user_id,
        )

        if project_access.membership is None:
            return SurveyAccess(
                project_access=project_access,
                survey_membership_role=None,
                survey_permissions=set(),
            )

        survey = surveys_repo.get_survey(
            db,
            project_id=project_id,
            survey_id=survey_id,
        )
        if survey is None:
            return SurveyAccess(
                project_access=project_access,
                survey_membership_role=None,
                survey_permissions=set(),
            )

        survey_membership_role = access_repo.get_survey_membership_role(
            db,
            project_id=project_id,
            survey_id=survey_id,
            membership_id=project_access.membership.id,
        )

        survey_permissions = (
            {permission.name for permission in survey_membership_role.role.permissions}
            if survey_membership_role is not None and survey_membership_role.role is not None
            else set()
        )

        return SurveyAccess(
            project_access=project_access,
            survey_membership_role=survey_membership_role,
            survey_permissions=survey_permissions,
        )


access_service = AccessService()


def require_project_permission(permission: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Require a project-scoped permission before running a service method.

    Use this on service methods that act at the project level, such as listing
    project resources, creating resources inside a project, or updating project
    settings.

    The decorated method must be called with these keyword arguments:
        - db: SQLAlchemy session
        - project_id: ID of the target project
        - actor: authenticated User performing the action

    Behavior:
        - If ``actor.platform_admin`` is True, the wrapped method runs
          immediately and no permission check is performed.
        - Otherwise, project access is resolved from the actor's membership and
          project role permissions.
        - The wrapped method runs only if the required permission is present.

    This decorator only checks authorization. It does not load project objects,
    validate request payloads, or check whether specific resources exist.

    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            
            actor = cast("User", kwargs["actor"])
            db = cast(Session, kwargs["db"])
            project_id = cast(int, kwargs["project_id"])

            if actor.platform_admin:
                return func(*args, **kwargs)

            access = access_service.get_project_access(
                db=db,
                project_id=project_id,
                user_id=actor.id,
            )
            access_rules.ensure_project_permission(access, permission)

            return func(*args, **kwargs)

        return wrapper

    return decorator


def require_survey_permission(permission: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Require a survey-scoped permission before running a service method.

    Use this on service methods that act on one specific survey, such as
    viewing, editing, deleting, publishing, or archiving a survey.

    The decorated method must be called with these keyword arguments:
        - db: SQLAlchemy session
        - project_id: ID of the project that owns the survey
        - survey_id: ID of the target survey
        - actor: authenticated User performing the action

    Behavior:
        - If ``actor.platform_admin`` is True, the wrapped method runs
          immediately and no permission check is performed.
        - Otherwise, survey access is resolved from the actor's project
          membership plus any survey-specific role assigned to that membership.
        - The wrapped method runs only if the required permission is present in
          the effective survey permission set.

    This decorator only checks authorization. It does not load and return the
    survey object for you. If the method needs the ORM survey instance, it
    should still fetch it itself.

    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            
            actor = cast("User", kwargs["actor"])
            db = cast(Session, kwargs["db"])
            project_id = cast(int, kwargs["project_id"])
            survey_id = cast(int, kwargs["survey_id"])
            
            if actor.platform_admin:
                return func(*args, **kwargs)

            
            access = access_service.get_survey_access(
                db=db,
                project_id=project_id,
                survey_id=survey_id,
                user_id=actor.id,
            )
            access_rules.ensure_survey_permission(access, permission)

            return func(*args, **kwargs)

        return wrapper

    return decorator
