from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import cast

import pytest
from psycopg.errors import CheckViolation, ForeignKeyViolation, NotNullViolation, UniqueViolation
from sqlalchemy import delete as sql_delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from app.schema.orm.core.project import Project
from app.schema.orm.core.response_store import ResponseStore
from app.schema.orm.core.response_subject_mapping import ResponseSubjectMapping
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.survey_access import SurveyPublicLink
from app.schema.orm.core.survey_submission import SurveySubmission
from app.schema.orm.core.user import User
from tests.integration.core.factories import (
    make_project,
    make_response_store,
    make_survey,
    make_survey_public_link,
    make_survey_version,
    make_user,
)

# ---------------------------------------------------------------------------
# Helpers — build a valid SurveySubmission for each channel
# ---------------------------------------------------------------------------


def _authenticated(
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
    user: User,
) -> SurveySubmission:
    sub = SurveySubmission()
    sub.project_id = project.id
    sub.survey_id = survey.id
    sub.survey_version_id = survey_version.id
    sub.response_store_id = response_store.id
    sub.submission_channel = "authenticated"
    sub.submitted_by_user_id = user.id
    sub.status = "pending"
    sub.is_anonymous = False
    return sub


def _public_link(
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
    link: SurveyPublicLink,
) -> SurveySubmission:
    sub = SurveySubmission()
    sub.project_id = project.id
    sub.survey_id = survey.id
    sub.survey_version_id = survey_version.id
    sub.response_store_id = response_store.id
    sub.submission_channel = "public_link"
    sub.public_link_id = link.id
    sub.status = "pending"
    sub.is_anonymous = False
    return sub


def _system(
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
) -> SurveySubmission:
    sub = SurveySubmission()
    sub.project_id = project.id
    sub.survey_id = survey.id
    sub.survey_version_id = survey_version.id
    sub.response_store_id = response_store.id
    sub.submission_channel = "system"
    sub.status = "pending"
    sub.is_anonymous = False
    return sub


# ---------------------------------------------------------------------------
# Happy path — one test per channel
# ---------------------------------------------------------------------------


def test_survey_submission_authenticated_can_be_created(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
    user: User,
) -> None:
    """An authenticated submission with all required fields is persisted correctly."""
    sub = _authenticated(project, survey, survey_version, response_store, user)
    db_session.add(sub)
    db_session.flush()

    saved = db_session.get(SurveySubmission, sub.id)
    assert saved is not None, "SurveySubmission was not persisted"
    assert saved.submission_channel == "authenticated", (
        f"submission_channel={saved.submission_channel!r}, expected 'authenticated'"
    )
    assert saved.submitted_by_user_id == user.id, (
        f"submitted_by_user_id={saved.submitted_by_user_id!r}, expected {user.id!r}"
    )
    assert saved.status == "pending", f"status={saved.status!r}, expected 'pending'"
    assert saved.is_anonymous is False, f"is_anonymous={saved.is_anonymous!r}, expected False"
    assert saved.created_at is not None, "created_at was not set by the server default"


def test_survey_submission_public_link_can_be_created(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
) -> None:
    """A public_link submission with a valid link is persisted correctly."""
    link = make_survey_public_link(survey.id)
    db_session.add(link)
    db_session.flush()

    sub = _public_link(project, survey, survey_version, response_store, link)
    db_session.add(sub)
    db_session.flush()

    saved = db_session.get(SurveySubmission, sub.id)
    assert saved is not None, "SurveySubmission was not persisted"
    assert saved.submission_channel == "public_link", (
        f"submission_channel={saved.submission_channel!r}, expected 'public_link'"
    )
    assert saved.public_link_id == link.id, f"public_link_id={saved.public_link_id!r}, expected {link.id!r}"
    assert saved.submitted_by_user_id is None, f"submitted_by_user_id={saved.submitted_by_user_id!r}, expected None"


def test_survey_submission_system_can_be_created(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
) -> None:
    """A system submission with no actor is persisted correctly."""
    sub = _system(project, survey, survey_version, response_store)
    db_session.add(sub)
    db_session.flush()

    saved = db_session.get(SurveySubmission, sub.id)
    assert saved is not None, "SurveySubmission was not persisted"
    assert saved.submission_channel == "system", f"submission_channel={saved.submission_channel!r}, expected 'system'"
    assert saved.submitted_by_user_id is None, f"submitted_by_user_id={saved.submitted_by_user_id!r}, expected None"
    assert saved.public_link_id is None, f"public_link_id={saved.public_link_id!r}, expected None"


# ---------------------------------------------------------------------------
# Cascade / SET NULL
# ---------------------------------------------------------------------------


def test_survey_submission_cascades_on_survey_delete(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
    user: User,
) -> None:
    """Deleting the survey removes all its submissions via CASCADE.

    Uses a SQL-level DELETE to let PostgreSQL own the full cascade chain,
    bypassing SQLAlchemy's ORM relationship handling which would otherwise
    interfere with deletion ordering.
    """
    sub = _authenticated(project, survey, survey_version, response_store, user)
    db_session.add(sub)
    db_session.flush()

    sub_id = sub.id
    db_session.execute(sql_delete(Survey).where(Survey.id == survey.id))
    db_session.expire_all()

    assert db_session.get(SurveySubmission, sub_id) is None, (
        "SurveySubmission should have been deleted when its survey was deleted"
    )


def test_survey_submission_authenticated_blocks_user_delete(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
) -> None:
    """Deleting a user with authenticated submissions is blocked by a CheckViolation.

    The FK uses ON DELETE SET NULL, but the CHECK constraint
    authenticated_requires_user makes NULL impossible for the authenticated
    channel — the two constraints together prevent hard-deleting such users.
    """
    submitter = make_user(auth0_user_id="auth0|sub-del", email="sub-del@example.com")
    db_session.add(submitter)
    db_session.flush()

    sub = _authenticated(project, survey, survey_version, response_store, submitter)
    db_session.add(sub)
    db_session.flush()

    with pytest.raises(IntegrityError) as exc_info:
        db_session.execute(sql_delete(User).where(User.id == submitter.id))

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_survey_submissions_authenticated_requires_user", (
        f"Expected constraint 'ck_survey_submissions_authenticated_requires_user', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


# ---------------------------------------------------------------------------
# NOT NULL
# ---------------------------------------------------------------------------


def test_survey_submission_requires_survey_version_id(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    response_store: ResponseStore,
    user: User,
) -> None:
    """survey_version_id is NOT NULL — omitting it raises an IntegrityError."""
    sub = SurveySubmission()
    sub.project_id = project.id
    sub.survey_id = survey.id
    sub.response_store_id = response_store.id
    sub.submission_channel = "authenticated"
    sub.submitted_by_user_id = user.id
    sub.status = "pending"
    sub.is_anonymous = False
    db_session.add(sub)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "survey_version_id", (
        f"Expected NOT NULL violation on 'survey_version_id', got '{column}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_submission_requires_submission_channel(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
    user: User,
) -> None:
    """submission_channel is NOT NULL — omitting it raises an IntegrityError."""
    sub = SurveySubmission()
    sub.project_id = project.id
    sub.survey_id = survey.id
    sub.survey_version_id = survey_version.id
    sub.response_store_id = response_store.id
    sub.submitted_by_user_id = user.id
    sub.status = "pending"
    sub.is_anonymous = False
    db_session.add(sub)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(NotNullViolation, exc_info.value.orig)
    column = orig.diag.column_name
    assert column == "submission_channel", (
        f"Expected NOT NULL violation on 'submission_channel', got '{column}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


# ---------------------------------------------------------------------------
# Status and channel valid values
# ---------------------------------------------------------------------------


def test_survey_submission_rejects_invalid_status(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
    user: User,
) -> None:
    """status must be one of: pending, stored, failed."""
    sub = _authenticated(project, survey, survey_version, response_store, user)
    sub.status = "invalid"
    db_session.add(sub)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_survey_submissions_status_valid", (
        f"Expected constraint 'ck_survey_submissions_status_valid', got '{constraint}'\nDB error: {exc_info.value}"
    )

    db_session.rollback()


@pytest.mark.parametrize("status", ["pending", "stored", "failed"])
def test_survey_submission_accepts_all_valid_statuses(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
    user: User,
    status: str,
) -> None:
    """Each of the three valid status values is accepted."""
    sub = _authenticated(project, survey, survey_version, response_store, user)
    sub.status = status
    db_session.add(sub)
    db_session.flush()

    assert sub.id is not None, f"Submission with status={status!r} was not persisted"

    db_session.rollback()


def test_survey_submission_rejects_invalid_channel(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
) -> None:
    """submission_channel must be one of: authenticated, public_link, system.

    No user or link is set so that authenticated_requires_user and
    public_link_requires_link_id both pass, leaving only submission_channel_valid
    to fire.
    """
    sub = SurveySubmission()
    sub.project_id = project.id
    sub.survey_id = survey.id
    sub.survey_version_id = survey_version.id
    sub.response_store_id = response_store.id
    sub.submission_channel = "invalid_channel"
    sub.status = "pending"
    sub.is_anonymous = False
    db_session.add(sub)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_survey_submissions_submission_channel_valid", (
        f"Expected constraint 'ck_survey_submissions_submission_channel_valid', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


# ---------------------------------------------------------------------------
# Timestamp ordering
# ---------------------------------------------------------------------------


def test_survey_submission_rejects_submitted_before_started(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
    user: User,
) -> None:
    """submitted_at must be >= started_at when both are set."""
    sub = _authenticated(project, survey, survey_version, response_store, user)
    sub.started_at = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
    sub.submitted_at = datetime(2024, 6, 1, 11, 0, 0, tzinfo=UTC)  # before started_at
    db_session.add(sub)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_survey_submissions_submitted_at_after_started_at", (
        f"Expected constraint 'ck_survey_submissions_submitted_at_after_started_at', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_submission_accepts_submitted_equals_started(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
    user: User,
) -> None:
    """submitted_at equal to started_at is a valid edge case (instant submission)."""
    ts = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
    sub = _authenticated(project, survey, survey_version, response_store, user)
    sub.started_at = ts
    sub.submitted_at = ts
    db_session.add(sub)
    db_session.flush()

    assert sub.id is not None, "Submission with submitted_at == started_at was not persisted"


# ---------------------------------------------------------------------------
# Channel consistency constraints
# ---------------------------------------------------------------------------


def test_survey_submission_authenticated_requires_user(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
) -> None:
    """authenticated channel must have submitted_by_user_id set."""
    sub = SurveySubmission()
    sub.project_id = project.id
    sub.survey_id = survey.id
    sub.survey_version_id = survey_version.id
    sub.response_store_id = response_store.id
    sub.submission_channel = "authenticated"
    # submitted_by_user_id intentionally omitted
    sub.status = "pending"
    sub.is_anonymous = False
    db_session.add(sub)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_survey_submissions_authenticated_requires_user", (
        f"Expected constraint 'ck_survey_submissions_authenticated_requires_user', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_submission_public_link_requires_link_id(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
) -> None:
    """public_link channel must have public_link_id set."""
    sub = SurveySubmission()
    sub.project_id = project.id
    sub.survey_id = survey.id
    sub.survey_version_id = survey_version.id
    sub.response_store_id = response_store.id
    sub.submission_channel = "public_link"
    # public_link_id intentionally omitted
    sub.status = "pending"
    sub.is_anonymous = False
    db_session.add(sub)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_survey_submissions_public_link_requires_link_id", (
        f"Expected constraint 'ck_survey_submissions_public_link_requires_link_id', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_submission_system_rejects_actor(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
    user: User,
) -> None:
    """system channel must have no submitted_by_user_id or public_link_id."""
    sub = _system(project, survey, survey_version, response_store)
    sub.submitted_by_user_id = user.id  # not allowed on system
    db_session.add(sub)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_survey_submission_authenticated_rejects_link_id(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
    user: User,
) -> None:
    """authenticated channel must not have public_link_id set."""
    link = make_survey_public_link(survey.id)
    db_session.add(link)
    db_session.flush()

    sub = _authenticated(project, survey, survey_version, response_store, user)
    sub.public_link_id = link.id  # not allowed on authenticated
    db_session.add(sub)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_survey_submission_public_link_rejects_user(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
    user: User,
) -> None:
    """public_link channel must not have submitted_by_user_id set."""
    link = make_survey_public_link(survey.id)
    db_session.add(link)
    db_session.flush()

    sub = _public_link(project, survey, survey_version, response_store, link)
    sub.submitted_by_user_id = user.id  # not allowed on public_link
    db_session.add(sub)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


# ---------------------------------------------------------------------------
# Anonymous constraints
# ---------------------------------------------------------------------------


def test_survey_submission_anonymous_has_no_user(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
    user: User,
) -> None:
    """is_anonymous=True must not have submitted_by_user_id set."""
    # authenticated satisfies authenticated_requires_user; then anonymous_has_no_user fires
    sub = _authenticated(project, survey, survey_version, response_store, user)
    sub.is_anonymous = True
    db_session.add(sub)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_survey_submissions_anonymous_has_no_user", (
        f"Expected constraint 'ck_survey_submissions_anonymous_has_no_user', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_submission_anonymous_has_no_subject(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
) -> None:
    """is_anonymous=True must not have pseudonymous_subject_id set."""
    # Create a real ResponseSubjectMapping so the FK doesn't fire before the CHECK
    rsm_user = make_user(auth0_user_id="auth0|rsm-anon", email="rsm-anon@example.com")
    db_session.add(rsm_user)
    db_session.flush()

    subject_id = uuid.uuid4()
    rsm = ResponseSubjectMapping()
    rsm.project_id = project.id
    rsm.user_id = rsm_user.id
    rsm.pseudonymous_subject_id = subject_id
    db_session.add(rsm)
    db_session.flush()

    sub = _system(project, survey, survey_version, response_store)
    sub.is_anonymous = True
    sub.pseudonymous_subject_id = subject_id  # not allowed when anonymous
    db_session.add(sub)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(CheckViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "ck_survey_submissions_anonymous_has_no_subject", (
        f"Expected constraint 'ck_survey_submissions_anonymous_has_no_subject', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


# ---------------------------------------------------------------------------
# FK same-project / same-survey constraints
# ---------------------------------------------------------------------------


def test_survey_submission_survey_must_belong_to_project(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
    user: User,
) -> None:
    """project_id must match the survey's project_id."""
    other_project = make_project(user.id, name="Other", slug="ss-other-proj")
    db_session.add(other_project)
    db_session.flush()

    sub = _authenticated(project, survey, survey_version, response_store, user)
    sub.project_id = other_project.id  # mismatch: survey belongs to project, not other_project
    db_session.add(sub)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(ForeignKeyViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "fk_survey_submissions_survey_same_project", (
        f"Expected constraint 'fk_survey_submissions_survey_same_project', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_submission_version_must_belong_to_survey(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
    user: User,
) -> None:
    """survey_version_id must belong to the same survey as survey_id."""
    other_store = make_response_store(project.id, user.id, name="other-store")
    db_session.add(other_store)
    db_session.flush()

    other_survey = make_survey(project.id, other_store.id, user.id, title="Other Survey")
    db_session.add(other_survey)
    db_session.flush()

    other_version = make_survey_version(other_survey.id, user.id, version_number=1)
    db_session.add(other_version)
    db_session.flush()

    sub = _authenticated(project, survey, survey_version, response_store, user)
    sub.survey_version_id = other_version.id  # version belongs to other_survey
    db_session.add(sub)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(ForeignKeyViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "fk_survey_submissions_version_same_survey", (
        f"Expected constraint 'fk_survey_submissions_version_same_survey', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_submission_store_must_belong_to_project(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
    user: User,
) -> None:
    """response_store_id must belong to the same project as project_id."""
    other_project = make_project(user.id, name="Other", slug="ss-store-proj")
    db_session.add(other_project)
    db_session.flush()

    store_in_other = make_response_store(other_project.id, user.id, name="other-store")
    db_session.add(store_in_other)
    db_session.flush()

    sub = _authenticated(project, survey, survey_version, response_store, user)
    sub.response_store_id = store_in_other.id  # store belongs to other_project
    db_session.add(sub)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(ForeignKeyViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "fk_survey_submissions_store_same_project", (
        f"Expected constraint 'fk_survey_submissions_store_same_project', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_submission_public_link_must_belong_to_survey(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
) -> None:
    """Create a public link for Survey B, try to use it on a submission for Survey A,
    and assert the DB rejects it with the expected constraint."""

    pl_user = make_user(auth0_user_id="auth0|pl-user", email="pl-user@example.com")
    db_session.add(pl_user)
    db_session.flush()

    pl_store = make_response_store(project.id, pl_user.id, name="pl-store")
    db_session.add(pl_store)
    db_session.flush()

    other_survey = make_survey(project.id, pl_store.id, pl_user.id, title="Other Survey PL")
    db_session.add(other_survey)
    db_session.flush()

    link_for_other = make_survey_public_link(other_survey.id)
    db_session.add(link_for_other)
    db_session.flush()

    sub = _public_link(project, survey, survey_version, response_store, link_for_other)
    # link belongs to other_survey but submission is for survey
    db_session.add(sub)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(ForeignKeyViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "fk_survey_submissions_public_link_same_survey", (
        f"Expected constraint 'fk_survey_submissions_public_link_same_survey', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


# ---------------------------------------------------------------------------
# Partial unique index on external_submission_id
# ---------------------------------------------------------------------------


def test_survey_submission_unique_external_id_within_store(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
    user: User,
) -> None:
    """Two submissions cannot share an external_submission_id within the same store."""
    sub_a = _authenticated(project, survey, survey_version, response_store, user)
    sub_a.external_submission_id = "ext-001"
    db_session.add(sub_a)
    db_session.flush()

    # Need a second user to satisfy the unique user constraint doesn't block us —
    # actually there's no unique user per submission; just add a second sub from same user
    # by rolling back and creating independently.
    # Use system channel for second sub to avoid "duplicate user" issues.
    sub_b = _system(project, survey, survey_version, response_store)
    sub_b.external_submission_id = "ext-001"  # duplicate within same store
    db_session.add(sub_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "uq_survey_submissions_external_submission_id", (
        f"Expected constraint 'uq_survey_submissions_external_submission_id', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()


def test_survey_submission_null_external_id_not_constrained(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
) -> None:
    """Multiple submissions with NULL external_submission_id are allowed (partial index)."""
    sub_a = _system(project, survey, survey_version, response_store)
    sub_a.external_submission_id = None
    db_session.add(sub_a)

    sub_b = _system(project, survey, survey_version, response_store)
    sub_b.external_submission_id = None
    db_session.add(sub_b)

    db_session.flush()

    assert sub_a.id != sub_b.id, f"Expected distinct submission IDs, got id={sub_a.id!r} for both"


def test_survey_submission_same_external_id_allowed_across_stores(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
    user: User,
) -> None:
    """The same external_submission_id is allowed in different response stores."""
    other_store = make_response_store(project.id, user.id, name="second-store")
    db_session.add(other_store)
    db_session.flush()

    sub_a = _authenticated(project, survey, survey_version, response_store, user)
    sub_a.external_submission_id = "ext-shared"
    db_session.add(sub_a)
    db_session.flush()

    sub_b = _system(project, survey, survey_version, other_store)
    sub_b.external_submission_id = "ext-shared"  # same ID, different store
    db_session.add(sub_b)
    db_session.flush()

    assert sub_a.id != sub_b.id, f"Expected distinct submission IDs across stores, got id={sub_a.id!r} for both"
