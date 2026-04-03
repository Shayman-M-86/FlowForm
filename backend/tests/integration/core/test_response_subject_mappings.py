from __future__ import annotations

import uuid
from typing import cast

import pytest
from psycopg.errors import NotNullViolation, UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from app.schema.orm.core.project import Project
from app.schema.orm.core.response_subject_mapping import ResponseSubjectMapping
from app.schema.orm.core.user import User
from tests.integration.core.factories import make_project, make_user


def test_response_subject_mapping_can_be_created(
    db_session: scoped_session[Session], project: Project, user: User
) -> None:
    """All fields are persisted and the server default populates created_at."""
    subject_id = uuid.uuid4()

    mapping = ResponseSubjectMapping()
    mapping.project_id = project.id
    mapping.user_id = user.id
    mapping.pseudonymous_subject_id = subject_id
    db_session.add(mapping)
    db_session.flush()

    saved = db_session.get(ResponseSubjectMapping, mapping.id)
    assert saved is not None, "ResponseSubjectMapping was not persisted"
    assert saved.project_id == project.id, f"project_id={saved.project_id!r}, expected {project.id!r}"
    assert saved.user_id == user.id, f"user_id={saved.user_id!r}, expected {user.id!r}"
    assert saved.pseudonymous_subject_id == subject_id, (
        f"pseudonymous_subject_id={saved.pseudonymous_subject_id!r}, expected {subject_id!r}"
    )
    assert saved.created_at is not None, "created_at was not set by the server default"


def test_response_subject_mapping_unique_project_user(
    db_session: scoped_session[Session], project: Project, user: User
) -> None:
    """A user can only have one pseudonymous identity per project."""
    mapping_a = ResponseSubjectMapping()
    mapping_a.project_id = project.id
    mapping_a.user_id = user.id
    mapping_a.pseudonymous_subject_id = uuid.uuid4()
    db_session.add(mapping_a)
    db_session.flush()

    mapping_b = ResponseSubjectMapping()
    mapping_b.project_id = project.id
    mapping_b.user_id = user.id
    mapping_b.pseudonymous_subject_id = uuid.uuid4()
    db_session.add(mapping_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "uq_response_subject_mappings_project_id_user_id", (
        f"Expected constraint 'uq_response_subject_mappings_project_id_user_id', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_response_subject_mapping_unique_project_subject(
    db_session: scoped_session[Session], project: Project, user: User
) -> None:
    """A pseudonymous subject ID can only be assigned once per project."""
    subject_id = uuid.uuid4()

    mapping_a = ResponseSubjectMapping()
    mapping_a.project_id = project.id
    mapping_a.user_id = user.id
    mapping_a.pseudonymous_subject_id = subject_id
    db_session.add(mapping_a)
    db_session.flush()

    other_user = make_user(auth0_user_id="auth0|u2", email="u2@example.com", display_name="U2")
    db_session.add(other_user)
    db_session.flush()

    mapping_b = ResponseSubjectMapping()
    mapping_b.project_id = project.id
    mapping_b.user_id = other_user.id
    mapping_b.pseudonymous_subject_id = subject_id
    db_session.add(mapping_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "uq_response_subject_mappings_project_id_pseudonymous_subject_id", (
        f"Expected constraint 'uq_response_subject_mappings_project_id_pseudonymous_subject_id',"
        f" got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_response_subject_mapping_same_user_allowed_across_projects(
    db_session: scoped_session[Session], user: User
) -> None:
    """The same user can have a pseudonymous identity in multiple projects."""
    project_a = make_project(user.id, name="A", slug="rsm-proj-a")
    project_b = make_project(user.id, name="B", slug="rsm-proj-b")
    db_session.add_all([project_a, project_b])
    db_session.flush()

    mapping_a = ResponseSubjectMapping()
    mapping_a.project_id = project_a.id
    mapping_a.user_id = user.id
    mapping_a.pseudonymous_subject_id = uuid.uuid4()
    db_session.add(mapping_a)

    mapping_b = ResponseSubjectMapping()
    mapping_b.project_id = project_b.id
    mapping_b.user_id = user.id
    mapping_b.pseudonymous_subject_id = uuid.uuid4()
    db_session.add(mapping_b)

    db_session.flush()

    assert mapping_a.id != mapping_b.id, (
        f"Expected distinct mapping IDs across projects, got id={mapping_a.id!r} for both"
    )


def test_response_subject_mapping_same_subject_id_allowed_across_projects(
    db_session: scoped_session[Session], user: User
) -> None:
    """The same pseudonymous subject ID may appear in different projects."""
    project_a = make_project(user.id, name="A", slug="rsm-subj-proj-a")
    project_b = make_project(user.id, name="B", slug="rsm-subj-proj-b")
    db_session.add_all([project_a, project_b])
    db_session.flush()

    shared_subject_id = uuid.uuid4()

    mapping_a = ResponseSubjectMapping()
    mapping_a.project_id = project_a.id
    mapping_a.user_id = user.id
    mapping_a.pseudonymous_subject_id = shared_subject_id

    other_user = make_user(auth0_user_id="auth0|rsm-u2", email="rsm-u2@example.com")
    db_session.add(other_user)
    db_session.flush()

    mapping_b = ResponseSubjectMapping()
    mapping_b.project_id = project_b.id
    mapping_b.user_id = other_user.id
    mapping_b.pseudonymous_subject_id = shared_subject_id

    db_session.add_all([mapping_a, mapping_b])
    db_session.flush()

    assert mapping_a.id != mapping_b.id, (
        f"Expected distinct mapping IDs, got id={mapping_a.id!r} for both"
    )


def test_response_subject_mapping_cascades_on_project_delete(
    db_session: scoped_session[Session], user: User
) -> None:
    """Deleting the project removes all its subject mappings."""
    project = make_project(user.id, slug="rsm-cascade-proj")
    db_session.add(project)
    db_session.flush()

    mapping = ResponseSubjectMapping()
    mapping.project_id = project.id
    mapping.user_id = user.id
    mapping.pseudonymous_subject_id = uuid.uuid4()
    db_session.add(mapping)
    db_session.flush()

    mapping_id = mapping.id
    db_session.delete(project)
    db_session.flush()
    db_session.expire_all()

    assert db_session.get(ResponseSubjectMapping, mapping_id) is None, (
        "Mapping should have been deleted when its project was deleted"
    )


def test_response_subject_mapping_cascades_on_user_delete(
    db_session: scoped_session[Session], project: Project
) -> None:
    """Deleting the user removes all their subject mappings."""
    user = make_user(auth0_user_id="auth0|rsm-del", email="rsm-del@example.com")
    db_session.add(user)
    db_session.flush()

    mapping = ResponseSubjectMapping()
    mapping.project_id = project.id
    mapping.user_id = user.id
    mapping.pseudonymous_subject_id = uuid.uuid4()
    db_session.add(mapping)
    db_session.flush()

    mapping_id = mapping.id
    db_session.delete(user)
    db_session.flush()
    db_session.expire_all()

    assert db_session.get(ResponseSubjectMapping, mapping_id) is None, (
        "Mapping should have been deleted when its user was deleted"
    )


def test_response_subject_mapping_requires_pseudonymous_subject_id(
    db_session: scoped_session[Session], project: Project, user: User
) -> None:
    """pseudonymous_subject_id is NOT NULL — omitting it raises an IntegrityError."""
    mapping = ResponseSubjectMapping()
    mapping.project_id = project.id
    mapping.user_id = user.id
    mapping.pseudonymous_subject_id = None  # type: ignore[assignment]
    db_session.add(mapping)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "pseudonymous_subject_id", (
        f"Expected NOT NULL violation on 'pseudonymous_subject_id', got '{column}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()
