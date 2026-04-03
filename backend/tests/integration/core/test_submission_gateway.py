"""
Integration tests for SubmissionGateway — the cross-database submission coordinator.

Each test uses the ``db_sessions`` fixture (DbSessions.core + DbSessions.response),
which gives two separate sessions bound to test-transaction-wrapped connections.
Commits inside the gateway release savepoints; the outer connection transactions
are rolled back by the fixture teardown, keeping the database clean.

Prerequisites (user, project, response_store, survey, survey_version) are created
via the factories and written through ``db_sessions.core`` directly, keeping the
sessions under the gateway's control for the full request lifecycle.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from app.schema.orm.core.response_subject_mapping import ResponseSubjectMapping
from app.services import LinkedSubmission, SubmissionGateway
from tests.integration.conftest import DbSessions
from tests.integration.core.factories import (
    make_project,
    make_response_store,
    make_survey,
    make_survey_version,
    make_user,
)


# ---------------------------------------------------------------------------
# Shared fixtures — scoped to function, wired to db_sessions.core
# ---------------------------------------------------------------------------


@pytest.fixture()
def gateway() -> SubmissionGateway:
    return SubmissionGateway()


@pytest.fixture()
def core_user(db_sessions: DbSessions) -> object:
    user = make_user(auth0_user_id="auth0|gw1", email="gw1@example.com")
    db_sessions.core.add(user)
    db_sessions.core.flush()
    return user


@pytest.fixture()
def core_project(core_user, db_sessions: DbSessions) -> object:
    project = make_project(core_user.id)
    db_sessions.core.add(project)
    db_sessions.core.flush()
    return project


@pytest.fixture()
def core_response_store(core_project, core_user, db_sessions: DbSessions) -> object:
    store = make_response_store(core_project.id, core_user.id)
    db_sessions.core.add(store)
    db_sessions.core.flush()
    return store


@pytest.fixture()
def core_survey(core_project, core_response_store, core_user, db_sessions: DbSessions) -> object:
    survey = make_survey(core_project.id, core_response_store.id, core_user.id)
    db_sessions.core.add(survey)
    db_sessions.core.flush()
    return survey


@pytest.fixture()
def core_survey_version(core_survey, core_user, db_sessions: DbSessions) -> object:
    version = make_survey_version(core_survey.id, core_user.id)
    db_sessions.core.add(version)
    db_sessions.core.flush()
    return version


# ---------------------------------------------------------------------------
# get_or_create_subject_mapping
# ---------------------------------------------------------------------------


def test_get_or_create_subject_mapping_creates_new_mapping(
    gateway: SubmissionGateway,
    db_sessions: DbSessions,
    core_user,
    core_project,
) -> None:
    mapping = gateway.get_or_create_subject_mapping(
        db_sessions.core,
        project_id=core_project.id,
        user_id=core_user.id,
    )

    assert mapping.id is not None
    assert mapping.project_id == core_project.id
    assert mapping.user_id == core_user.id
    assert isinstance(mapping.pseudonymous_subject_id, uuid.UUID)


def test_get_or_create_subject_mapping_is_idempotent(
    gateway: SubmissionGateway,
    db_sessions: DbSessions,
    core_user,
    core_project,
) -> None:
    first = gateway.get_or_create_subject_mapping(
        db_sessions.core,
        project_id=core_project.id,
        user_id=core_user.id,
    )
    second = gateway.get_or_create_subject_mapping(
        db_sessions.core,
        project_id=core_project.id,
        user_id=core_user.id,
    )

    assert first.id == second.id
    assert first.pseudonymous_subject_id == second.pseudonymous_subject_id


# ---------------------------------------------------------------------------
# create_linked_submission — system channel
# ---------------------------------------------------------------------------


def test_create_linked_submission_system_channel(
    gateway: SubmissionGateway,
    db_sessions: DbSessions,
    core_project,
    core_response_store,
    core_survey,
    core_survey_version,
) -> None:
    result = gateway.create_linked_submission(
        db_sessions.core,
        db_sessions.response,
        project_id=core_project.id,
        survey_id=core_survey.id,
        survey_version_id=core_survey_version.id,
        response_store_id=core_response_store.id,
        submission_channel="system",
    )

    assert isinstance(result, LinkedSubmission)

    # Core side
    assert result.core_submission.id is not None
    assert result.core_submission.status == "stored"
    assert result.core_submission.submission_channel == "system"
    assert result.core_submission.project_id == core_project.id

    # Response side
    assert result.response_submission.id is not None
    assert result.response_submission.core_submission_id == result.core_submission.id
    assert result.response_submission.project_id == core_project.id

    # No identity data expected
    assert result.subject_mapping is None
    assert result.user is None
    assert result.answers == []


def test_create_linked_submission_with_answers(
    gateway: SubmissionGateway,
    db_sessions: DbSessions,
    core_project,
    core_response_store,
    core_survey,
    core_survey_version,
) -> None:
    answers = [
        {"question_key": "q1", "answer_family": "field", "answer_value": {"value": "hello"}},
        {"question_key": "q2", "answer_family": "rating", "answer_value": {"value": 4}},
    ]

    result = gateway.create_linked_submission(
        db_sessions.core,
        db_sessions.response,
        project_id=core_project.id,
        survey_id=core_survey.id,
        survey_version_id=core_survey_version.id,
        response_store_id=core_response_store.id,
        submission_channel="system",
        answers=answers,
    )

    assert len(result.answers) == 2
    keys = {a.question_key for a in result.answers}
    assert keys == {"q1", "q2"}
    assert all(a.submission_id == result.response_submission.id for a in result.answers)


# ---------------------------------------------------------------------------
# create_linked_submission — authenticated channel with pseudonymity
# ---------------------------------------------------------------------------


def test_create_linked_submission_authenticated_channel(
    gateway: SubmissionGateway,
    db_sessions: DbSessions,
    core_user,
    core_project,
    core_response_store,
    core_survey,
    core_survey_version,
) -> None:
    mapping = gateway.get_or_create_subject_mapping(
        db_sessions.core,
        project_id=core_project.id,
        user_id=core_user.id,
    )

    result = gateway.create_linked_submission(
        db_sessions.core,
        db_sessions.response,
        project_id=core_project.id,
        survey_id=core_survey.id,
        survey_version_id=core_survey_version.id,
        response_store_id=core_response_store.id,
        submission_channel="authenticated",
        submitted_by_user_id=core_user.id,
        pseudonymous_subject_id=mapping.pseudonymous_subject_id,
    )

    # Core holds the real user_id
    assert result.core_submission.submitted_by_user_id == core_user.id
    assert result.core_submission.pseudonymous_subject_id == mapping.pseudonymous_subject_id

    # Response holds only the pseudonymous UUID — no user_id
    assert result.response_submission.pseudonymous_subject_id == mapping.pseudonymous_subject_id
    assert not hasattr(result.response_submission, "submitted_by_user_id")


# ---------------------------------------------------------------------------
# load_linked_submission
# ---------------------------------------------------------------------------


def test_load_linked_submission_returns_none_for_missing_core_id(
    gateway: SubmissionGateway,
    db_sessions: DbSessions,
) -> None:
    result = gateway.load_linked_submission(
        db_sessions.core,
        db_sessions.response,
        core_submission_id=999_999,
    )
    assert result is None


def test_load_linked_submission_basic(
    gateway: SubmissionGateway,
    db_sessions: DbSessions,
    core_project,
    core_response_store,
    core_survey,
    core_survey_version,
) -> None:
    created = gateway.create_linked_submission(
        db_sessions.core,
        db_sessions.response,
        project_id=core_project.id,
        survey_id=core_survey.id,
        survey_version_id=core_survey_version.id,
        response_store_id=core_response_store.id,
        submission_channel="system",
    )

    loaded = gateway.load_linked_submission(
        db_sessions.core,
        db_sessions.response,
        core_submission_id=created.core_submission.id,
    )

    assert loaded is not None
    assert loaded.core_submission.id == created.core_submission.id
    assert loaded.response_submission.core_submission_id == created.core_submission.id


def test_load_linked_submission_include_answers(
    gateway: SubmissionGateway,
    db_sessions: DbSessions,
    core_project,
    core_response_store,
    core_survey,
    core_survey_version,
) -> None:
    answers = [
        {"question_key": "q1", "answer_family": "field", "answer_value": {"value": "test"}},
    ]
    created = gateway.create_linked_submission(
        db_sessions.core,
        db_sessions.response,
        project_id=core_project.id,
        survey_id=core_survey.id,
        survey_version_id=core_survey_version.id,
        response_store_id=core_response_store.id,
        submission_channel="system",
        answers=answers,
    )

    loaded = gateway.load_linked_submission(
        db_sessions.core,
        db_sessions.response,
        core_submission_id=created.core_submission.id,
        include_answers=True,
    )

    assert loaded is not None
    assert len(loaded.answers) == 1
    assert loaded.answers[0].question_key == "q1"


def test_load_linked_submission_resolve_identity(
    gateway: SubmissionGateway,
    db_sessions: DbSessions,
    core_user,
    core_project,
    core_response_store,
    core_survey,
    core_survey_version,
) -> None:
    """Reverse lookup: answer -> pseudonymous_subject_id -> mapping -> user."""
    mapping = gateway.get_or_create_subject_mapping(
        db_sessions.core,
        project_id=core_project.id,
        user_id=core_user.id,
    )

    created = gateway.create_linked_submission(
        db_sessions.core,
        db_sessions.response,
        project_id=core_project.id,
        survey_id=core_survey.id,
        survey_version_id=core_survey_version.id,
        response_store_id=core_response_store.id,
        submission_channel="authenticated",
        submitted_by_user_id=core_user.id,
        pseudonymous_subject_id=mapping.pseudonymous_subject_id,
    )

    loaded = gateway.load_linked_submission(
        db_sessions.core,
        db_sessions.response,
        core_submission_id=created.core_submission.id,
        resolve_identity=True,
    )

    assert loaded is not None
    assert loaded.subject_mapping is not None
    assert loaded.subject_mapping.user_id == core_user.id
    assert loaded.subject_mapping.pseudonymous_subject_id == mapping.pseudonymous_subject_id
    assert loaded.user is not None
    assert loaded.user.id == core_user.id
