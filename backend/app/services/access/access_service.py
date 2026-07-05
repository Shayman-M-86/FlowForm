from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any, TypeVar

from flask import g
from sqlalchemy.orm import Session

from app.domain import access_rules
from app.repositories import access_repo as ar
from app.repositories import surveys_repo as sr
from app.schema.orm.core import ProjectMembership, SurveyMembershipRole, User

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


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
        membership = ar.get_project_membership(
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

        survey = sr.get_survey(
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

        survey_membership_role = ar.get_survey_membership_role(
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


@dataclass(frozen=True, slots=True)
class RbacRequirement:
    """RBAC metadata attached to a protected view function."""

    permission: str

    def to_openapi(self) -> dict[str, object]:
        return {"permission": self.permission}


def _get_or_load_actor() -> User:
    """Return the current actor, loading it from Auth0 sub if not cached."""
    actor = getattr(g, "actor", None)
    if actor is not None:
        return actor

    from app.core.extensions import auth
    from app.db.context import get_core_db
    from app.services.users import UserService

    users_service = UserService()
    actor = users_service.get_user_by_sub(db=get_core_db(), auth0_user_id=auth.get_current_user_sub())
    g.actor = actor
    return actor


def require_project_permission(permission: str) -> Callable[[F], F]:
    """Require a project-scoped permission on a Flask view function.

    Reads ``project_id`` from the route kwargs, resolves the actor and project
    access, enforces the permission, then caches both on ``flask.g``.

    Platform admins bypass the project membership check.
    """
    requirement = RbacRequirement(permission=permission)

    def decorator(view: F) -> F:
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            from app.db.context import get_core_db

            actor = _get_or_load_actor()

            if actor.platform_admin:
                g.project_access = None
                return view(*args, **kwargs)

            project_id: int = kwargs["project_id"]
            access = access_service.get_project_access(
                db=get_core_db(),
                project_id=project_id,
                user_id=actor.id,
            )
            access_rules.ensure_project_permission(access, permission)
            g.project_access = access
            return view(*args, **kwargs)

        wrapped.__flowform_rbac__ = requirement  # type: ignore[attr-defined]
        return wrapped  # type: ignore[return-value]

    return decorator


def require_survey_permission(permission: str) -> Callable[[F], F]:
    """Require a survey-scoped permission on a Flask view function.

    Reads ``project_id`` and ``survey_id`` from the route kwargs, resolves the
    actor and survey access, enforces the permission, then caches both on
    ``flask.g``.

    Platform admins bypass the membership check.
    """
    requirement = RbacRequirement(permission=permission)

    def decorator(view: F) -> F:
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            from app.db.context import get_core_db

            actor = _get_or_load_actor()

            if actor.platform_admin:
                g.survey_access = None
                return view(*args, **kwargs)

            project_id: int = kwargs["project_id"]
            survey_id: int = kwargs["survey_id"]
            access = access_service.get_survey_access(
                db=get_core_db(),
                project_id=project_id,
                survey_id=survey_id,
                user_id=actor.id,
            )
            access_rules.ensure_survey_permission(access, permission)
            g.survey_access = access
            return view(*args, **kwargs)

        wrapped.__flowform_rbac__ = requirement  # type: ignore[attr-defined]
        return wrapped  # type: ignore[return-value]

    return decorator
