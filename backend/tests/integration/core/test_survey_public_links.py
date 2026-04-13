from __future__ import annotations

from typing import cast

import pytest
from psycopg.errors import CheckViolation, NotNullViolation, UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from app.schema.orm.core.survey import Survey
from app.schema.orm.core.survey_access import SurveyLink
from tests.integration.core.factories import make_token_pair


def test_survey_public_link_can_be_created(
    db_session: scoped_session[Session], survey: Survey
) -> None:
    """All fields are persisted and server defaults populate is_active and created_at."""
    _, prefix, token_hash = make_token_pair()

    link = SurveyLink()
    link.survey_id = survey.id
    link.token_prefix = prefix
    link.token_hash = token_hash
    db_session.add(link)
    db_session.flush()

    saved = db_session.get(SurveyLink, link.id)
    assert saved is not None, "SurveyLink was not persisted"
    assert saved.survey_id == survey.id, f"survey_id={saved.survey_id!r}, expected {survey.id!r}"
    assert saved.token_prefix == prefix, f"token_prefix={saved.token_prefix!r}, expected {prefix!r}"
    assert saved.token_hash == token_hash, f"token_hash={saved.token_hash!r}, expected {token_hash!r}"
    assert saved.is_active is True, f"is_active={saved.is_active!r}, expected True from server default"
    assert saved.assigned_email is None, f"assigned_email={saved.assigned_email!r}, expected None"
    assert saved.expires_at is None, f"expires_at={saved.expires_at!r}, expected None"
    assert saved.created_at is not None, "created_at was not set by the server default"


def test_survey_public_link_unique_token_hash(
    db_session: scoped_session[Session], survey: Survey
) -> None:
    """token_hash must be globally unique — two links cannot share the same hash."""
    _, prefix_a, token_hash = make_token_pair()

    link_a = SurveyLink()
    link_a.survey_id = survey.id
    link_a.token_prefix = prefix_a
    link_a.token_hash = token_hash
    db_session.add(link_a)
    db_session.flush()

    _, prefix_b, _ = make_token_pair()

    link_b = SurveyLink()
    link_b.survey_id = survey.id
    link_b.token_prefix = prefix_b
    link_b.token_hash = token_hash
    db_session.add(link_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "uq_survey_links_token_hash", (
        f"Expected constraint 'uq_survey_links_token_hash', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_public_link_unique_prefix_within_survey(
    db_session: scoped_session[Session], survey: Survey
) -> None:
    """A token_prefix must be unique within a survey."""
    _, token_prefix, hash_a = make_token_pair()

    link_a = SurveyLink()
    link_a.survey_id = survey.id
    link_a.token_prefix = token_prefix
    link_a.token_hash = hash_a
    db_session.add(link_a)
    db_session.flush()

    _, _, hash_b = make_token_pair()

    link_b = SurveyLink()
    link_b.survey_id = survey.id
    link_b.token_prefix = token_prefix
    link_b.token_hash = hash_b
    db_session.add(link_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "uq_survey_links_survey_id_token_prefix", (
        f"Expected constraint 'uq_survey_links_survey_id_token_prefix', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_public_link_rejects_short_token_prefix(
    db_session: scoped_session[Session], survey: Survey
) -> None:
    """token_prefix must be between 8 and 32 characters."""
    _, _, token_hash = make_token_pair()

    link = SurveyLink()
    link.survey_id = survey.id
    link.token_prefix = "short"  # 5 chars — below the 8-char minimum
    link.token_hash = token_hash
    db_session.add(link)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_survey_links_token_prefix_len", (
        f"Expected constraint 'ck_survey_links_token_prefix_len', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_public_link_rejects_short_token_hash(
    db_session: scoped_session[Session], survey: Survey
) -> None:
    """token_hash must be at least 32 characters."""
    _, prefix, _ = make_token_pair()

    link = SurveyLink()
    link.survey_id = survey.id
    link.token_prefix = prefix
    link.token_hash = "tooshort"  # 8 chars — below the 32-char minimum
    db_session.add(link)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_survey_links_token_hash_len", (
        f"Expected constraint 'ck_survey_links_token_hash_len', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_public_link_requires_token_prefix(
    db_session: scoped_session[Session], survey: Survey
) -> None:
    """token_prefix is NOT NULL — omitting it raises an IntegrityError."""
    _, _, token_hash = make_token_pair()

    link = SurveyLink()
    link.survey_id = survey.id
    link.token_prefix = None  # type: ignore[assignment]
    link.token_hash = token_hash
    db_session.add(link)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "token_prefix", (
        f"Expected NOT NULL violation on 'token_prefix', got '{column}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_public_link_requires_token_hash(
    db_session: scoped_session[Session], survey: Survey
) -> None:
    """token_hash is NOT NULL — omitting it raises an IntegrityError."""
    _, prefix, _ = make_token_pair()

    link = SurveyLink()
    link.survey_id = survey.id
    link.token_prefix = prefix
    link.token_hash = None  # type: ignore[assignment]
    db_session.add(link)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "token_hash", (
        f"Expected NOT NULL violation on 'token_hash', got '{column}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_public_link_cascades_on_survey_delete(
    db_session: scoped_session[Session], survey: Survey
) -> None:
    """Deleting the survey removes all its public links."""
    _, prefix, token_hash = make_token_pair()

    link = SurveyLink()
    link.survey_id = survey.id
    link.token_prefix = prefix
    link.token_hash = token_hash
    db_session.add(link)
    db_session.flush()

    link_id = link.id
    db_session.delete(survey)
    db_session.flush()
    db_session.expire_all()

    assert db_session.get(SurveyLink, link_id) is None, (
        "SurveyLink should have been deleted when its survey was deleted"
    )
