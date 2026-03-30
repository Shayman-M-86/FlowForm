from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from app.models.core.project import Project, ProjectMembership, ProjectRole
from app.models.core.response_store import ResponseStore
from app.models.core.response_subject_mapping import ResponseSubjectMapping
from app.models.core.survey import Survey, SurveyVersion
from app.models.core.survey_access import SurveyPublicLink
from app.models.core.survey_submission import SurveySubmission
from app.models.core.user import User


def make_user(
    auth0_user_id: str = "auth0|u1",
    email: str = "u1@example.com",
    display_name: str | None = "U1",
) -> User:
    user = User()
    user.auth0_user_id = auth0_user_id
    user.email = email
    user.display_name = display_name
    return user


def make_project(
    user_id: int,
    name: str = "Test Project",
    slug: str = "test-project",
) -> Project:
    project = Project()
    project.name = name
    project.slug = slug
    project.created_by_user_id = user_id
    return project


def make_project_role(
    project_id: int,
    name: str = "admin",
    is_system_role: bool = True,
) -> ProjectRole:
    role = ProjectRole()
    role.project_id = project_id
    role.name = name
    role.is_system_role = is_system_role
    return role


def make_response_store(
    project_id: int,
    user_id: int,
    name: str = "main-store",
) -> ResponseStore:
    store = ResponseStore()
    store.project_id = project_id
    store.name = name
    store.store_type = "platform_postgres"
    store.connection_reference = {"kind": "postgres"}
    store.created_by_user_id = user_id
    return store


def make_survey(
    project_id: int,
    response_store_id: int,
    user_id: int,
    title: str = "Customer Survey",
) -> Survey:
    survey = Survey()
    survey.project_id = project_id
    survey.title = title
    survey.default_response_store_id = response_store_id
    survey.created_by_user_id = user_id
    return survey


def make_survey_version(
    survey_id: int,
    user_id: int,
    version_number: int = 1,
    status: str = "draft",
) -> SurveyVersion:
    version = SurveyVersion()
    version.survey_id = survey_id
    version.version_number = version_number
    version.status = status
    version.created_by_user_id = user_id
    return version


@pytest.fixture
def user(db_session: scoped_session[Session]) -> User:
    user = make_user()
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def project(db_session: scoped_session[Session], user: User) -> Project:
    project = make_project(user.id)
    db_session.add(project)
    db_session.flush()
    return project


@pytest.fixture
def project_role(db_session: scoped_session[Session], project: Project) -> ProjectRole:
    role = make_project_role(project.id)
    db_session.add(role)
    db_session.flush()
    return role


@pytest.fixture
def response_store(db_session: scoped_session[Session], project: Project, user: User) -> ResponseStore:
    store = make_response_store(project.id, user.id)
    db_session.add(store)
    db_session.flush()
    return store


@pytest.fixture
def survey(db_session: scoped_session[Session], project: Project, response_store: ResponseStore, user: User) -> Survey:
    survey = make_survey(project.id, response_store.id, user.id)
    db_session.add(survey)
    db_session.flush()
    return survey


@pytest.fixture
def survey_version(db_session: scoped_session[Session], survey: Survey, user: User) -> SurveyVersion:
    version = make_survey_version(survey.id, user.id)
    db_session.add(version)
    db_session.flush()
    return version


def test_user_unique_email(db_session: scoped_session[Session]) -> None:
    user_a = make_user(auth0_user_id="auth0|a", email="dup@example.com")
    db_session.add(user_a)
    db_session.flush()

    user_b = make_user(auth0_user_id="auth0|b", email="dup@example.com")
    db_session.add(user_b)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_user_unique_auth0_user_id(db_session: scoped_session[Session]) -> None:
    user_a = make_user(auth0_user_id="auth0|same", email="one@example.com")
    db_session.add(user_a)
    db_session.flush()

    user_b = make_user(auth0_user_id="auth0|same", email="two@example.com")
    db_session.add(user_b)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_project_unique_slug(db_session: scoped_session[Session], user: User):
    project_a = make_project(user.id, name="One", slug="same")
    db_session.add(project_a)
    db_session.flush()

    project_b = make_project(user.id, name="Two", slug="same")
    db_session.add(project_b)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_project_role_unique_name_within_project(db_session: scoped_session[Session], project: Project):
    role_a = make_project_role(project.id, name="editor")
    db_session.add(role_a)
    db_session.flush()

    role_b = make_project_role(project.id, name="editor")
    db_session.add(role_b)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_project_membership_unique_user_project(db_session: scoped_session[Session], user: User, project: Project):
    membership_a = ProjectMembership()
    membership_a.user_id = user.id
    membership_a.project_id = project.id
    db_session.add(membership_a)
    db_session.flush()

    membership_b = ProjectMembership()
    membership_b.user_id = user.id
    membership_b.project_id = project.id
    db_session.add(membership_b)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_response_store_unique_name_within_project(db_session: scoped_session[Session], project: Project, user: User):
    store_a = ResponseStore()
    store_a.project_id = project.id
    store_a.name = "warehouse"
    store_a.store_type = "platform_postgres"
    store_a.connection_reference = {"dsn": "x"}
    store_a.created_by_user_id = user.id
    db_session.add(store_a)
    db_session.flush()

    store_b = ResponseStore()
    store_b.project_id = project.id
    store_b.name = "warehouse"
    store_b.store_type = "platform_postgres"
    store_b.connection_reference = {"dsn": "y"}
    store_b.created_by_user_id = user.id
    db_session.add(store_b)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_response_subject_mapping_unique_project_user(
    db_session: scoped_session[Session], project: Project, user: User
):
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

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_response_subject_mapping_unique_project_subject(
    db_session: scoped_session[Session], project: Project, user: User
):
    subject_id = uuid.uuid4()

    mapping_a = ResponseSubjectMapping()
    mapping_a.project_id = project.id
    mapping_a.user_id = user.id
    mapping_a.pseudonymous_subject_id = subject_id
    db_session.add(mapping_a)
    db_session.flush()

    other_user = make_user(
        auth0_user_id="auth0|u2",
        email="u2@example.com",
        display_name="U2",
    )
    db_session.add(other_user)
    db_session.flush()

    mapping_b = ResponseSubjectMapping()
    mapping_b.project_id = project.id
    mapping_b.user_id = other_user.id
    mapping_b.pseudonymous_subject_id = subject_id
    db_session.add(mapping_b)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_survey_version_unique_version_number_per_survey(
    db_session: scoped_session[Session], survey: Survey, user: User
):
    version_a = make_survey_version(survey.id, user.id, version_number=1)
    db_session.add(version_a)
    db_session.flush()

    version_b = make_survey_version(survey.id, user.id, version_number=1)
    db_session.add(version_b)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_survey_public_link_unique_token_hash(db_session: scoped_session[Session], survey: Survey):
    link_a = SurveyPublicLink()
    link_a.survey_id = survey.id
    link_a.token_prefix = "abc"
    link_a.token_hash = "hash-1"
    db_session.add(link_a)
    db_session.flush()

    link_b = SurveyPublicLink()
    link_b.survey_id = survey.id
    link_b.token_prefix = "def"
    link_b.token_hash = "hash-1"
    db_session.add(link_b)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_survey_public_link_unique_prefix_within_survey(db_session: scoped_session[Session], survey: Survey):
    link_a = SurveyPublicLink()
    link_a.survey_id = survey.id
    link_a.token_prefix = "same"
    link_a.token_hash = "hash-1"
    db_session.add(link_a)
    db_session.flush()

    link_b = SurveyPublicLink()
    link_b.survey_id = survey.id
    link_b.token_prefix = "same"
    link_b.token_hash = "hash-2"
    db_session.add(link_b)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_survey_submission_can_be_created(
    db_session: scoped_session[Session],
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
    user: User,
):
    submission = SurveySubmission()
    submission.project_id = project.id
    submission.survey_id = survey.id
    submission.survey_version_id = survey_version.id
    submission.response_store_id = response_store.id
    submission.submission_channel = "authenticated"
    submission.submitted_by_user_id = user.id
    submission.status = "pending"
    submission.is_anonymous = False
    db_session.add(submission)
    db_session.flush()

    saved = db_session.get(SurveySubmission, submission.id)
    assert saved is not None
    assert saved.submitted_by_user_id == user.id
    assert saved.submission_channel == "authenticated"
    assert saved.status == "pending"
