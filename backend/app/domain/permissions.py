from dataclasses import dataclass, fields


@dataclass(frozen=True)
class PermissionGroup:
    """Base class for grouping related permission strings."""

    def values(self) -> tuple[str, ...]:
        return tuple(getattr(self, field.name) for field in fields(self))


@dataclass(frozen=True)
class ProjectPermissionSet(PermissionGroup):
    """Project-level permissions."""
    
    edit: str = "project:edit"
    delete: str = "project:delete"
    manage_members: str = "project:manage_members"
    manage_roles: str = "project:manage_roles"


@dataclass(frozen=True)
class SurveyPermissionSet(PermissionGroup):
    """Survey-level permissions that can be granted via survey roles."""

    view: str = "survey:view"
    create: str = "survey:create"
    edit: str = "survey:edit"
    delete: str = "survey:delete"
    publish: str = "survey:publish"
    archive: str = "survey:archive"


@dataclass(frozen=True)
class SubmissionPermissionSet(PermissionGroup):
    """Submission-level permissions."""

    view: str = "submission:view"


@dataclass(frozen=True)
class PermissionsSet:
    """Centralized collection of all permission sets for the application."""

    project: ProjectPermissionSet = ProjectPermissionSet()
    survey: SurveyPermissionSet = SurveyPermissionSet()
    submission: SubmissionPermissionSet = SubmissionPermissionSet()

    def all(self) -> tuple[str, ...]:
        return (
            *self.project.values(),
            *self.survey.values(),
            *self.submission.values(),
        )


PERMISSIONS = PermissionsSet()
