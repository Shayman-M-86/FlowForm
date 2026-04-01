from __future__ import annotations

from typing import cast

import pytest
from psycopg.errors import CheckViolation, NotNullViolation, UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from app.models.core.project import Project
from app.models.core.response_store import ResponseStore
from app.models.core.user import User
from tests.integration.core.factories import make_project, make_response_store, make_user


def test_response_store_can_be_created(
    db_session: scoped_session[Session], project: Project, user: User
) -> None:
    """All fields are persisted and the server defaults populate created_at and updated_at."""
    store = make_response_store(project.id, user.id, name="primary")
    db_session.add(store)
    db_session.flush()

    saved = db_session.get(ResponseStore, store.id)
    assert saved is not None, "ResponseStore was not persisted"
    assert saved.project_id == project.id, f"project_id={saved.project_id!r}, expected {project.id!r}"
    assert saved.name == "primary", f"name={saved.name!r}, expected 'primary'"
    assert saved.store_type == "platform_postgres", f"store_type={saved.store_type!r}, expected 'platform_postgres'"
    assert saved.created_by_user_id == user.id, f"created_by_user_id={saved.created_by_user_id!r}, expected {user.id!r}"
    assert saved.created_at is not None, "created_at was not set by the server default"
    assert saved.updated_at is not None, "updated_at was not set by the server default"


def test_response_store_created_by_user_id_nullable(
    db_session: scoped_session[Session], project: Project
) -> None:
    """A response store can be created without a creator."""
    store = make_response_store(project.id, user_id=None)  # type: ignore[arg-type]
    db_session.add(store)
    db_session.flush()

    saved = db_session.get(ResponseStore, store.id)
    assert saved is not None, "ResponseStore without a creator was not persisted"
    assert saved.created_by_user_id is None, f"created_by_user_id={saved.created_by_user_id!r}, expected None"


def test_response_store_creator_set_null_on_user_delete(
    db_session: scoped_session[Session], project: Project
) -> None:
    """Deleting the creator nullifies created_by_user_id rather than cascading."""
    creator = make_user(auth0_user_id="auth0|rsdel", email="rsdel@example.com")
    db_session.add(creator)
    db_session.flush()

    store = make_response_store(project.id, creator.id, name="to-orphan")
    db_session.add(store)
    db_session.flush()

    db_session.delete(creator)
    db_session.flush()

    db_session.refresh(store)
    assert store.created_by_user_id is None, (
        f"created_by_user_id={store.created_by_user_id!r}, expected None after creator deleted"
    )


def test_response_store_unique_name_within_project(
    db_session: scoped_session[Session], project: Project, user: User
) -> None:
    """Two stores in the same project cannot share a name."""
    store_a = make_response_store(project.id, user.id, name="warehouse")
    db_session.add(store_a)
    db_session.flush()

    store_b = make_response_store(project.id, user.id, name="warehouse")
    db_session.add(store_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "uq_response_stores_project_id_name", (
        f"Expected constraint 'uq_response_stores_project_id_name', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_response_store_same_name_allowed_across_projects(
    db_session: scoped_session[Session], user: User
) -> None:
    """Store name uniqueness is scoped to a project — different projects may reuse names."""
    project_a = make_project(user.id, name="A", slug="rs-proj-a")
    project_b = make_project(user.id, name="B", slug="rs-proj-b")
    db_session.add_all([project_a, project_b])
    db_session.flush()

    store_a = make_response_store(project_a.id, user.id, name="warehouse")
    store_b = make_response_store(project_b.id, user.id, name="warehouse")
    db_session.add_all([store_a, store_b])
    db_session.flush()

    assert store_a.id != store_b.id, (
        f"Expected distinct store IDs across projects, got id={store_a.id!r} for both"
    )


def test_response_store_rejects_invalid_store_type(
    db_session: scoped_session[Session], project: Project, user: User
) -> None:
    """store_type must be 'platform_postgres' or 'external_postgres'."""
    store = make_response_store(project.id, user.id)
    store.store_type = "s3_bucket"
    db_session.add(store)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_response_stores_store_type_valid", (
        f"Expected constraint 'ck_response_stores_store_type_valid', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_response_store_rejects_non_object_connection_reference(
    db_session: scoped_session[Session], project: Project, user: User
) -> None:
    """connection_reference must be a JSON object, not an array or scalar."""
    store = make_response_store(project.id, user.id)
    store.connection_reference = ["not", "an", "object"]  # type: ignore[assignment]
    db_session.add(store)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_response_stores_connection_reference_is_object", (
        f"Expected constraint 'ck_response_stores_connection_reference_is_object', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_response_store_requires_name(
    db_session: scoped_session[Session], project: Project, user: User
) -> None:
    """name is NOT NULL — omitting it raises an IntegrityError."""
    store = make_response_store(project.id, user.id)
    store.name = None  # type: ignore[assignment]
    db_session.add(store)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "name", (
        f"Expected NOT NULL violation on 'name', got '{column}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_response_store_requires_store_type(
    db_session: scoped_session[Session], project: Project, user: User
) -> None:
    """store_type is NOT NULL — omitting it raises an IntegrityError."""
    store = make_response_store(project.id, user.id)
    store.store_type = None  # type: ignore[assignment]
    db_session.add(store)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "store_type", (
        f"Expected NOT NULL violation on 'store_type', got '{column}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_response_store_requires_connection_reference(
    db_session: scoped_session[Session], project: Project, user: User
) -> None:
    """Setting connection_reference to None triggers the object check constraint.

    psycopg3 serialises Python None on a JSONB column as JSON null (not SQL NULL),
    so jsonb_typeof returns null rather than 'object' and the check fires first.
    """
    store = make_response_store(project.id, user.id)
    store.connection_reference = None  # type: ignore[assignment]
    db_session.add(store)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_response_stores_connection_reference_is_object", (
        f"Expected constraint 'ck_response_stores_connection_reference_is_object', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()
