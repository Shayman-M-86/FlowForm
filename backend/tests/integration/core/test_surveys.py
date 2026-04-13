from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest
from psycopg.errors import CheckViolation, ForeignKeyViolation, UniqueViolation
from sqlalchemy import delete as sql_delete
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session, scoped_session

from app.schema.orm.core.project import Project
from app.schema.orm.core.response_store import ResponseStore
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.user import User
from tests.integration.core.factories import (
    make_project,
    make_response_store,
    make_survey,
    make_survey_version,
    make_user,
)

# ---------------------------------------------------------------------------
# Survey
# ---------------------------------------------------------------------------


def test_survey_can_be_created(
    db_session: scoped_session[Session],
    project: Project,
    response_store: ResponseStore,
    user: User,
) -> None:
    """All fields are persisted and server defaults populate created_at and updated_at."""
    survey = make_survey(project.id, response_store.id, user.id, title="Onboarding Survey")
    db_session.add(survey)
    db_session.flush()

    saved = db_session.get(Survey, survey.id)
    assert saved is not None, "Survey was not persisted"
    assert saved.project_id == project.id, f"project_id={saved.project_id!r}, expected {project.id!r}"
    assert saved.title == "Onboarding Survey", f"title={saved.title!r}, expected 'Onboarding Survey'"
    assert saved.created_by_user_id == user.id, f"created_by_user_id={saved.created_by_user_id!r}, expected {user.id!r}"
    assert saved.visibility == "private", f"visibility={saved.visibility!r}, expected 'private' default"
    assert saved.created_at is not None, "created_at was not set by the server default"
    assert saved.updated_at is not None, "updated_at was not set by the server default"


def test_survey_creator_set_null_on_user_delete(
    db_session: scoped_session[Session],
    project: Project,
    response_store: ResponseStore,
) -> None:
    """Deleting the creator nullifies created_by_user_id rather than cascading."""
    creator = make_user(auth0_user_id="auth0|sv-del", email="sv-del@example.com")
    db_session.add(creator)
    db_session.flush()

    survey = make_survey(project.id, response_store.id, creator.id)
    db_session.add(survey)
    db_session.flush()

    db_session.execute(sql_delete(User).where(User.id == creator.id))
    db_session.expire_all()

    saved = db_session.get(Survey, survey.id)
    assert saved is not None, "Survey should still exist after creator was deleted"
    assert saved.created_by_user_id is None, (
        f"created_by_user_id={saved.created_by_user_id!r}, expected None after creator deleted"
    )


def test_survey_cascades_on_project_delete(
    db_session: scoped_session[Session],
    project: Project,
    response_store: ResponseStore,
    user: User,
) -> None:
    """Deleting the project removes all its surveys."""
    survey = make_survey(project.id, response_store.id, user.id)
    db_session.add(survey)
    db_session.flush()

    survey_id = survey.id
    db_session.execute(sql_delete(Project).where(Project.id == project.id))
    db_session.expire_all()

    assert db_session.get(Survey, survey_id) is None, "Survey should have been deleted when its project was deleted"


def test_survey_requires_title(
    db_session: scoped_session[Session],
    project: Project,
    response_store: ResponseStore,
    user: User,
) -> None:
    """title is NOT NULL — omitting it raises an IntegrityError."""
    survey = make_survey(project.id, response_store.id, user.id)
    survey.title = None  # type: ignore[assignment]
    db_session.add(survey)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_survey_rejects_invalid_visibility(
    db_session: scoped_session[Session],
    project: Project,
    response_store: ResponseStore,
    user: User,
) -> None:
    """visibility must be one of: private, link_only, public."""
    survey = make_survey(project.id, response_store.id, user.id)
    survey.visibility = "hidden"
    db_session.add(survey)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_surveys_visibility_valid", (
        f"Expected constraint 'ck_surveys_visibility_valid', got '{constraint}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


@pytest.mark.parametrize("visibility", ["private", "link_only", "public"])
def test_survey_accepts_valid_visibility_values(
    db_session: scoped_session[Session],
    project: Project,
    response_store: ResponseStore,
    user: User,
    visibility: str,
) -> None:
    """Each of the three visibility values is accepted."""
    survey = make_survey(project.id, response_store.id, user.id)
    survey.visibility = visibility
    if visibility == "public":
        survey.public_slug = f"slug-{visibility}"
    db_session.add(survey)
    db_session.flush()

    assert survey.id is not None, f"Survey with visibility={visibility!r} was not persisted"

    db_session.rollback()


def test_survey_link_only_rejects_public_slug(
    db_session: scoped_session[Session],
    project: Project,
    response_store: ResponseStore,
    user: User,
) -> None:
    """A survey with visibility='link_only' must not have a public_slug."""
    survey = make_survey(project.id, response_store.id, user.id)
    survey.visibility = "link_only"
    survey.public_slug = "link-only-slug"
    db_session.add(survey)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_surveys_slug_requires_public_visibility", (
        f"Expected constraint 'ck_surveys_slug_requires_public_visibility', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_public_visibility_requires_slug(
    db_session: scoped_session[Session],
    project: Project,
    response_store: ResponseStore,
    user: User,
) -> None:
    """A survey with visibility='public' must have a public_slug."""
    survey = make_survey(project.id, response_store.id, user.id)
    survey.visibility = "public"
    survey.public_slug = None  # omitted intentionally
    db_session.add(survey)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_surveys_public_requires_slug", (
        f"Expected constraint 'ck_surveys_public_requires_slug', got '{constraint}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_slug_requires_public_visibility(
    db_session: scoped_session[Session],
    project: Project,
    response_store: ResponseStore,
    user: User,
) -> None:
    """A survey with a public_slug must have visibility='public'."""
    survey = make_survey(project.id, response_store.id, user.id)
    survey.visibility = "private"
    survey.public_slug = "my-slug"
    db_session.add(survey)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_surveys_slug_requires_public_visibility", (
        f"Expected constraint 'ck_surveys_slug_requires_public_visibility', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_public_slug_is_unique(
    db_session: scoped_session[Session],
    project: Project,
    response_store: ResponseStore,
    user: User,
) -> None:
    """Two surveys cannot share the same public_slug."""
    survey_a = make_survey(project.id, response_store.id, user.id, title="A")
    survey_a.visibility = "public"
    survey_a.public_slug = "shared-slug"
    db_session.add(survey_a)
    db_session.flush()

    survey_b = make_survey(project.id, response_store.id, user.id, title="B")
    survey_b.visibility = "public"
    survey_b.public_slug = "shared-slug"
    db_session.add(survey_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "surveys_public_slug_key", (
        f"Expected constraint 'surveys_public_slug_key', got '{constraint}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_default_store_must_belong_to_project(
    db_session: scoped_session[Session],
    project: Project,
    response_store: ResponseStore,
    user: User,
) -> None:
    """default_response_store_id must reference a store in the same project."""
    other_project = make_project(user.id, name="Other", slug="sv-store-proj")
    db_session.add(other_project)
    db_session.flush()

    store_in_other = make_response_store(other_project.id, user.id, name="other-store")
    db_session.add(store_in_other)
    db_session.flush()

    survey = make_survey(project.id, response_store.id, user.id)
    survey.default_response_store_id = store_in_other.id  # belongs to other_project
    db_session.add(survey)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(ForeignKeyViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "fk_surveys_default_store_same_project", (
        f"Expected constraint 'fk_surveys_default_store_same_project', got '{constraint}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_published_version_must_belong_to_survey(
    db_session: scoped_session[Session],
    project: Project,
    response_store: ResponseStore,
    user: User,
) -> None:
    """published_version_id is validated by a trigger — it must reference a published version of the same survey."""
    survey_a = make_survey(project.id, response_store.id, user.id, title="A")
    survey_b = make_survey(project.id, response_store.id, user.id, title="B")
    db_session.add_all([survey_a, survey_b])
    db_session.flush()

    version_b = make_survey_version(survey_b.id, user.id, status="published")
    version_b.compiled_schema = {"questions": []}
    version_b.published_at = datetime(2024, 1, 1, tzinfo=UTC)
    db_session.add(version_b)
    db_session.flush()

    survey_a.published_version_id = version_b.id  # version belongs to survey_b
    db_session.add(survey_a)

    with pytest.raises(ProgrammingError) as exc_info:
        db_session.flush()

    assert "published_version_id must reference" in str(exc_info.value.orig), (
        f"Expected trigger message about published_version_id, got: {exc_info.value}"
    )

    db_session.rollback()


# ---------------------------------------------------------------------------
# SurveyVersion
# ---------------------------------------------------------------------------


def test_survey_version_can_be_created(
    db_session: scoped_session[Session],
    survey: Survey,
    user: User,
) -> None:
    """All fields are persisted and server defaults populate created_at and updated_at."""
    version = make_survey_version(survey.id, user.id, version_number=1)
    db_session.add(version)
    db_session.flush()

    saved = db_session.get(SurveyVersion, version.id)
    assert saved is not None, "SurveyVersion was not persisted"
    assert saved.survey_id == survey.id, f"survey_id={saved.survey_id!r}, expected {survey.id!r}"
    assert saved.version_number == 1, f"version_number={saved.version_number!r}, expected 1"
    assert saved.status == "draft", f"status={saved.status!r}, expected 'draft'"
    assert saved.created_by_user_id == user.id, f"created_by_user_id={saved.created_by_user_id!r}, expected {user.id!r}"
    assert saved.created_at is not None, "created_at was not set by the server default"
    assert saved.updated_at is not None, "updated_at was not set by the server default"


def test_survey_version_unique_version_number_per_survey(
    db_session: scoped_session[Session], survey: Survey, user: User
) -> None:
    """Two versions of the same survey cannot share a version_number."""
    version_a = make_survey_version(survey.id, user.id, version_number=1)
    db_session.add(version_a)
    db_session.flush()

    version_b = make_survey_version(survey.id, user.id, version_number=1)
    db_session.add(version_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "uq_survey_versions_survey_id_version_number", (
        f"Expected constraint 'uq_survey_versions_survey_id_version_number', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_version_same_version_number_allowed_across_surveys(
    db_session: scoped_session[Session],
    project: Project,
    response_store: ResponseStore,
    user: User,
) -> None:
    """The same version_number may be used in different surveys."""
    survey_a = make_survey(project.id, response_store.id, user.id, title="A")
    survey_b = make_survey(project.id, response_store.id, user.id, title="B")
    db_session.add_all([survey_a, survey_b])
    db_session.flush()

    v_a = make_survey_version(survey_a.id, user.id, version_number=1)
    v_b = make_survey_version(survey_b.id, user.id, version_number=1)
    db_session.add_all([v_a, v_b])
    db_session.flush()

    assert v_a.id != v_b.id, f"Expected distinct version IDs across surveys, got id={v_a.id!r} for both"


def test_survey_version_rejects_invalid_status(db_session: scoped_session[Session], survey: Survey, user: User) -> None:
    """status must be one of: draft, published, archived."""
    version = make_survey_version(survey.id, user.id)
    version.status = "inactive"
    db_session.add(version)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_survey_versions_status_valid", (
        f"Expected constraint 'ck_survey_versions_status_valid', got '{constraint}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


@pytest.mark.parametrize("status", ["draft", "published", "archived"])
def test_survey_version_accepts_valid_status_values(
    db_session: scoped_session[Session], survey: Survey, user: User, status: str
) -> None:
    """Each of the three valid status values is accepted."""
    version = make_survey_version(survey.id, user.id)
    version.status = status
    if status == "published":
        version.compiled_schema = {"fields": []}
        version.published_at = datetime(2024, 1, 1, tzinfo=UTC)
    db_session.add(version)
    db_session.flush()

    assert version.id is not None, f"SurveyVersion with status={status!r} was not persisted"

    db_session.rollback()


def test_survey_version_rejects_non_positive_version_number(
    db_session: scoped_session[Session], survey: Survey, user: User
) -> None:
    """version_number must be greater than zero."""
    version = make_survey_version(survey.id, user.id)
    version.version_number = 0
    db_session.add(version)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_survey_versions_version_number_positive", (
        f"Expected constraint 'ck_survey_versions_version_number_positive', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_version_published_requires_schema_and_timestamp(
    db_session: scoped_session[Session], survey: Survey, user: User
) -> None:
    """A published version must have compiled_schema and published_at set."""
    version = make_survey_version(survey.id, user.id)
    version.status = "published"
    # compiled_schema and published_at intentionally omitted
    db_session.add(version)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_survey_versions_published_requires_schema_and_timestamp", (
        f"Expected constraint 'ck_survey_versions_published_requires_schema_and_timestamp', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_version_only_one_published_per_survey(
    db_session: scoped_session[Session], survey: Survey, user: User
) -> None:
    """Only one non-deleted published version may exist per survey at a time."""
    v1 = make_survey_version(survey.id, user.id, version_number=1)
    v1.status = "published"
    v1.compiled_schema = {"fields": []}
    v1.published_at = datetime(2024, 1, 1, tzinfo=UTC)
    db_session.add(v1)
    db_session.flush()

    v2 = make_survey_version(survey.id, user.id, version_number=2)
    v2.status = "published"
    v2.compiled_schema = {"fields": []}
    v2.published_at = datetime(2024, 6, 1, tzinfo=UTC)
    db_session.add(v2)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "uq_survey_versions_one_published", (
        f"Expected constraint 'uq_survey_versions_one_published', got '{constraint}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_version_deleted_published_does_not_block_new_published(
    db_session: scoped_session[Session], survey: Survey, user: User
) -> None:
    """A soft-deleted published version does not count toward the one-published limit."""
    v1 = make_survey_version(survey.id, user.id, version_number=1)
    v1.status = "published"
    v1.compiled_schema = {"fields": []}
    v1.published_at = datetime(2024, 1, 1, tzinfo=UTC)
    v1.deleted_at = datetime(2024, 3, 1, tzinfo=UTC)  # soft-deleted
    db_session.add(v1)
    db_session.flush()

    v2 = make_survey_version(survey.id, user.id, version_number=2)
    v2.status = "published"
    v2.compiled_schema = {"fields": []}
    v2.published_at = datetime(2024, 6, 1, tzinfo=UTC)
    db_session.add(v2)
    db_session.flush()

    assert v2.id is not None, "Second published version should be allowed when first is soft-deleted"


def test_survey_version_cascades_on_survey_delete(
    db_session: scoped_session[Session],
    project: Project,
    response_store: ResponseStore,
    user: User,
) -> None:
    """Deleting the survey removes all its versions."""
    survey = make_survey(project.id, response_store.id, user.id)
    db_session.add(survey)
    db_session.flush()

    version = make_survey_version(survey.id, user.id)
    db_session.add(version)
    db_session.flush()

    version_id = version.id
    db_session.execute(sql_delete(Survey).where(Survey.id == survey.id))
    db_session.expire_all()

    assert db_session.get(SurveyVersion, version_id) is None, (
        "SurveyVersion should have been deleted when its survey was deleted"
    )


def test_survey_version_creator_set_null_on_user_delete(db_session: scoped_session[Session], survey: Survey) -> None:
    """Deleting the creator nullifies created_by_user_id rather than cascading."""
    creator = make_user(auth0_user_id="auth0|sv-cr-del", email="sv-cr-del@example.com")
    db_session.add(creator)
    db_session.flush()

    version = make_survey_version(survey.id, creator.id)
    db_session.add(version)
    db_session.flush()

    db_session.execute(sql_delete(User).where(User.id == creator.id))
    db_session.expire_all()

    saved = db_session.get(SurveyVersion, version.id)
    assert saved is not None, "SurveyVersion should still exist after creator was deleted"
    assert saved.created_by_user_id is None, (
        f"created_by_user_id={saved.created_by_user_id!r}, expected None after creator deleted"
    )
