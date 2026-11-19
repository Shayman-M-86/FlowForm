from dataclasses import dataclass, fields
from typing import Literal

ProjectPermission = Literal[
    "project:edit",
    "project:delete",
    "project:manage_members",
    "project:manage_roles",
    "survey:view",
    "survey:create",
    "survey:edit",
    "survey:delete",
    "survey:publish",
    "survey:archive",
    "submission:view",
]

SurveyPermission = Literal[
    "survey:view",
    "survey:create",
    "survey:edit",
    "survey:delete",
    "survey:publish",
    "survey:archive",
    "submission:view",
]


type PermissionName = ProjectPermission | SurveyPermission


@dataclass(frozen=True)
class PermissionGroup:
    """Base class for grouping related permission strings."""

    def values(self) -> tuple[PermissionName, ...]:
        return tuple(getattr(self, field.name) for field in fields(self))


@dataclass(frozen=True)
class ProjectPermissionSet(PermissionGroup):
    """Project-level permissions."""

    edit: PermissionName = "project:edit"
    delete: PermissionName = "project:delete"
    manage_members: PermissionName = "project:manage_members"
    manage_roles: PermissionName = "project:manage_roles"


@dataclass(frozen=True)
class SurveyPermissionSet(PermissionGroup):
    """Survey-level permissions that can be granted via survey roles."""

    view: PermissionName = "survey:view"
    create: PermissionName = "survey:create"
    edit: PermissionName = "survey:edit"
    delete: PermissionName = "survey:delete"
    publish: PermissionName = "survey:publish"
    archive: PermissionName = "survey:archive"


@dataclass(frozen=True)
class SubmissionPermissionSet(PermissionGroup):
    """Submission-level permissions."""

    view: PermissionName = "submission:view"


@dataclass(frozen=True)
class PermissionsSet:
    """Centralized collection of all permission sets for the application."""

    project: ProjectPermissionSet = ProjectPermissionSet()
    survey: SurveyPermissionSet = SurveyPermissionSet()
    submission: SubmissionPermissionSet = SubmissionPermissionSet()

    def all(self) -> tuple[PermissionName, ...]:
        return (
            *self.project.values(),
            *self.survey.values(),
            *self.submission.values(),
        )


PERMISSIONS = PermissionsSet()
