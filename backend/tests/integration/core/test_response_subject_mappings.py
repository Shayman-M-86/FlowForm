from __future__ import annotations

import uuid
from typing import cast

import pytest
from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from app.models.core.project import Project
from app.models.core.response_subject_mapping import ResponseSubjectMapping
from app.models.core.user import User
from tests.integration.core.factories import make_user


def test_response_subject_mapping_unique_project_user(
    db_session: scoped_session[Session], project: Project, user: User
) -> None:
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
