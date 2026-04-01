from __future__ import annotations

from typing import cast

import pytest
from psycopg.errors import CheckViolation, NotNullViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from app.models.core.audit_log import AuditLog
from app.models.core.user import User
from tests.integration.core.factories import make_audit_log


def test_audit_log_can_be_created(
    db_session: scoped_session[Session],
    user: User,
) -> None:
    log = make_audit_log(
        action="published",
        entity_type="survey",
        entity_id=42,
        user_id=user.id,
        metadata={"reason": "manual trigger"},
    )
    db_session.add(log)
    db_session.flush()

    saved = db_session.get(AuditLog, log.id)
    assert saved is not None, "AuditLog was not persisted"
    assert saved.user_id == user.id, (
        f"user_id={saved.user_id!r}, expected {user.id!r}"
    )
    assert saved.action == "published", (
        f"action={saved.action!r}, expected 'published'"
    )
    assert saved.entity_type == "survey", (
        f"entity_type={saved.entity_type!r}, expected 'survey'"
    )
    assert saved.entity_id == 42, (
        f"entity_id={saved.entity_id!r}, expected 42"
    )
    assert saved.log_metadata == {"reason": "manual trigger"}, (
        f"log_metadata={saved.log_metadata!r}, expected {{'reason': 'manual trigger'}}"
    )
    assert saved.created_at is not None, "created_at was not set by the server default"


def test_audit_log_can_be_created_without_user(
    db_session: scoped_session[Session],
) -> None:
    log = make_audit_log(action="system_sweep", entity_type="project", user_id=None)
    db_session.add(log)
    db_session.flush()

    saved = db_session.get(AuditLog, log.id)
    assert saved is not None, "Anonymous AuditLog was not persisted"
    assert saved.user_id is None, (
        f"user_id={saved.user_id!r}, expected None for a system action"
    )


def test_audit_log_metadata_can_be_null(
    db_session: scoped_session[Session],
    user: User,
) -> None:
    log = make_audit_log(user_id=user.id, metadata=None)
    db_session.add(log)
    db_session.flush()

    saved = db_session.get(AuditLog, log.id)
    assert saved is not None, "AuditLog with null metadata was not persisted"
    assert saved.log_metadata is None, (
        f"log_metadata={saved.log_metadata!r}, expected None"
    )


def test_audit_log_requires_action(
    db_session: scoped_session[Session],
    user: User,
) -> None:
    log = make_audit_log(user_id=user.id)
    log.action = None  # type: ignore[assignment]
    db_session.add(log)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "action", (
        f"Expected NOT NULL violation on 'action', got '{column}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_audit_log_requires_entity_type(
    db_session: scoped_session[Session],
    user: User,
) -> None:
    log = make_audit_log(user_id=user.id)
    log.entity_type = None  # type: ignore[assignment]
    db_session.add(log)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "entity_type", (
        f"Expected NOT NULL violation on 'entity_type', got '{column}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_audit_log_rejects_non_object_metadata(
    db_session: scoped_session[Session],
    user: User,
) -> None:
    log = make_audit_log(user_id=user.id, metadata=None)
    log.log_metadata = ["not", "an", "object"]  # type: ignore[assignment]
    db_session.add(log)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_audit_logs_metadata_is_object", (
        f"Expected constraint 'ck_audit_logs_metadata_is_object', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()
