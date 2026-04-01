from __future__ import annotations

from typing import cast

import pytest
from psycopg.errors import CheckViolation, ForeignKeyViolation, NotNullViolation, UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from app.models.core.project import Project, ProjectMembership, ProjectRole
from app.models.core.user import User
from tests.integration.core.factories import make_project, make_project_role, make_user

# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


def test_project_can_be_created(db_session: scoped_session[Session], user: User) -> None:
    """All fields are persisted and the server default populates created_at."""
    project = make_project(user.id, name="My Project", slug="my-project")
    db_session.add(project)
    db_session.flush()

    saved = db_session.get(Project, project.id)
    assert saved is not None, "Project was not persisted"
    assert saved.name == "My Project", f"name={saved.name!r}, expected 'My Project'"
    assert saved.slug == "my-project", f"slug={saved.slug!r}, expected 'my-project'"
    assert saved.created_by_user_id == user.id, f"created_by_user_id={saved.created_by_user_id!r}, expected {user.id!r}"
    assert saved.created_at is not None, "created_at was not set by the server default"


def test_project_created_by_user_id_nullable(db_session: scoped_session[Session]) -> None:
    """A project can be created without a creator (system-created projects)."""
    project = make_project(user_id=None, slug="orphan-project")  # type: ignore[arg-type]
    db_session.add(project)
    db_session.flush()

    saved = db_session.get(Project, project.id)
    assert saved is not None, "Project without a creator was not persisted"
    assert saved.created_by_user_id is None, f"created_by_user_id={saved.created_by_user_id!r}, expected None"


def test_project_creator_set_null_on_user_delete(
    db_session: scoped_session[Session],
) -> None:
    """Deleting the creator nullifies created_by_user_id rather than cascading."""
    creator = make_user(auth0_user_id="auth0|del", email="del@example.com")
    db_session.add(creator)
    db_session.flush()

    project = make_project(creator.id, slug="del-project")
    db_session.add(project)
    db_session.flush()

    db_session.delete(creator)
    db_session.flush()

    db_session.refresh(project)
    assert project.created_by_user_id is None, (
        f"created_by_user_id={project.created_by_user_id!r}, expected None after creator deleted"
    )


def test_project_unique_slug(db_session: scoped_session[Session], user: User) -> None:
    """Two projects cannot share the same slug."""
    project_a = make_project(user.id, name="One", slug="same")
    db_session.add(project_a)
    db_session.flush()

    project_b = make_project(user.id, name="Two", slug="same")
    db_session.add(project_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "projects_slug_key", (
        f"Expected constraint 'projects_slug_key', got '{constraint}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_project_requires_name(db_session: scoped_session[Session], user: User) -> None:
    """name is NOT NULL — omitting it raises an IntegrityError."""
    project = make_project(user.id, slug="no-name")
    project.name = None  # type: ignore[assignment]
    db_session.add(project)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "name", f"Expected NOT NULL violation on 'name', got '{column}'\nDB error: {exc_info.value}"

    db_session.rollback()


# ---------------------------------------------------------------------------
# ProjectRole
# ---------------------------------------------------------------------------


def test_project_role_can_be_created(db_session: scoped_session[Session], project: Project) -> None:
    """All fields are persisted and the server default populates created_at."""
    role = make_project_role(project.id, name="viewer", is_system_role=False)
    db_session.add(role)
    db_session.flush()

    saved = db_session.get(ProjectRole, role.id)
    assert saved is not None, "ProjectRole was not persisted"
    assert saved.project_id == project.id, f"project_id={saved.project_id!r}, expected {project.id!r}"
    assert saved.name == "viewer", f"name={saved.name!r}, expected 'viewer'"
    assert saved.is_system_role is False, f"is_system_role={saved.is_system_role!r}, expected False"
    assert saved.created_at is not None, "created_at was not set by the server default"


def test_project_role_is_system_role_defaults_to_false(db_session: scoped_session[Session], project: Project) -> None:
    """is_system_role has a server default of false when not explicitly set."""
    role = ProjectRole()
    role.project_id = project.id
    role.name = "guest"
    db_session.add(role)
    db_session.flush()

    db_session.refresh(role)
    assert role.is_system_role is False, f"is_system_role={role.is_system_role!r}, expected False from server default"


def test_project_role_unique_name_within_project(db_session: scoped_session[Session], project: Project) -> None:
    """Two roles in the same project cannot share a name."""
    role_a = make_project_role(project.id, name="editor")
    db_session.add(role_a)
    db_session.flush()

    role_b = make_project_role(project.id, name="editor")
    db_session.add(role_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "uq_project_roles_project_name", (
        f"Expected constraint 'uq_project_roles_project_name', got '{constraint}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_project_role_same_name_allowed_across_projects(db_session: scoped_session[Session], user: User) -> None:
    """Role name uniqueness is scoped to a project — different projects may reuse names."""
    project_a = make_project(user.id, name="A", slug="proj-a")
    project_b = make_project(user.id, name="B", slug="proj-b")
    db_session.add_all([project_a, project_b])
    db_session.flush()

    role_a = make_project_role(project_a.id, name="admin")
    role_b = make_project_role(project_b.id, name="admin")
    db_session.add_all([role_a, role_b])
    db_session.flush()

    assert role_a.id != role_b.id, f"Expected distinct role IDs across projects, got id={role_a.id!r} for both"


def test_project_role_requires_name(db_session: scoped_session[Session], project: Project) -> None:
    """name is NOT NULL — omitting it raises an IntegrityError."""
    role = ProjectRole()
    role.project_id = project.id
    role.name = None  # type: ignore[assignment]
    db_session.add(role)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "name", f"Expected NOT NULL violation on 'name', got '{column}'\nDB error: {exc_info.value}"

    db_session.rollback()


# ---------------------------------------------------------------------------
# ProjectMembership
# ---------------------------------------------------------------------------


def test_project_membership_can_be_created(db_session: scoped_session[Session], user: User, project: Project) -> None:
    """A membership with no role is persisted and created_at is set by the server."""
    membership = ProjectMembership()
    membership.user_id = user.id
    membership.project_id = project.id
    db_session.add(membership)
    db_session.flush()

    saved = db_session.get(ProjectMembership, membership.id)
    assert saved is not None, "ProjectMembership was not persisted"
    assert saved.user_id == user.id, f"user_id={saved.user_id!r}, expected {user.id!r}"
    assert saved.project_id == project.id, f"project_id={saved.project_id!r}, expected {project.id!r}"
    assert saved.role_id is None, f"role_id={saved.role_id!r}, expected None"
    assert saved.created_at is not None, "created_at was not set by the server default"


def test_project_membership_status_defaults_to_active(
    db_session: scoped_session[Session], user: User, project: Project
) -> None:
    """status has a server default of 'active' when not explicitly set."""
    membership = ProjectMembership()
    membership.user_id = user.id
    membership.project_id = project.id
    db_session.add(membership)
    db_session.flush()

    db_session.refresh(membership)
    assert membership.status == "active", f"status={membership.status!r}, expected 'active' from server default"


def test_project_membership_can_have_role(
    db_session: scoped_session[Session], user: User, project: Project, project_role: ProjectRole
) -> None:
    """A membership can optionally reference a role within the same project."""
    membership = ProjectMembership()
    membership.user_id = user.id
    membership.project_id = project.id
    membership.role_id = project_role.id
    db_session.add(membership)
    db_session.flush()

    saved = db_session.get(ProjectMembership, membership.id)
    assert saved is not None, "ProjectMembership with role was not persisted"
    assert saved.role_id == project_role.id, f"role_id={saved.role_id!r}, expected {project_role.id!r}"


def test_project_membership_rejects_invalid_status(
    db_session: scoped_session[Session], user: User, project: Project
) -> None:
    """status must be 'active' or 'invited' — any other value is rejected."""
    membership = ProjectMembership()
    membership.user_id = user.id
    membership.project_id = project.id
    membership.status = "banned"
    db_session.add(membership)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_project_memberships_status_valid", (
        f"Expected constraint 'ck_project_memberships_status_valid', got '{constraint}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_project_membership_unique_user_project(
    db_session: scoped_session[Session], user: User, project: Project
) -> None:
    """A user can only have one membership record per project."""
    membership_a = ProjectMembership()
    membership_a.user_id = user.id
    membership_a.project_id = project.id
    db_session.add(membership_a)
    db_session.flush()

    membership_b = ProjectMembership()
    membership_b.user_id = user.id
    membership_b.project_id = project.id
    db_session.add(membership_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "uq_project_memberships_user_project", (
        f"Expected constraint 'uq_project_memberships_user_project', got '{constraint}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_project_membership_role_must_belong_to_same_project(
    db_session: scoped_session[Session], user: User, project: Project
) -> None:
    """A membership cannot reference a role that belongs to a different project."""
    other_project = make_project(user.id, name="Other", slug="other-project")
    db_session.add(other_project)
    db_session.flush()

    role_on_other = make_project_role(other_project.id, name="admin")
    db_session.add(role_on_other)
    db_session.flush()

    membership = ProjectMembership()
    membership.user_id = user.id
    membership.project_id = project.id
    membership.role_id = role_on_other.id
    db_session.add(membership)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(ForeignKeyViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "fk_project_memberships_role_same_project", (
        f"Expected constraint 'fk_project_memberships_role_same_project', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()
