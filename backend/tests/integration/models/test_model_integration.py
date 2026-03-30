from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.extensions import db
from app.models.core.project import Project, ProjectMembership, ProjectRole
from app.models.core.response_store import ResponseStore
from app.models.core.response_subject_mapping import ResponseSubjectMapping
from app.models.core.survey import Survey, SurveyVersion
from app.models.core.survey_access import SurveyPublicLink
from app.models.core.survey_submission import SurveySubmission
from app.models.core.user import User
from app.models.response.submission import Submission
from app.models.response.submission_answer import SubmissionAnswer
from app.models.response.submission_event import SubmissionEvent


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


def make_project(user_id: int, name: str = "Test Project", slug: str = "test-project") -> Project:
    project = Project()
    project.name = name
    project.slug = slug
    project.created_by_user_id = user_id
    return project


def make_project_role(project_id: int, name: str = "admin", is_system_role: bool = True) -> ProjectRole:
    role = ProjectRole()
    role.project_id = project_id
    role.name = name
    role.is_system_role = is_system_role
    return role


def make_response_store(project_id: int, user_id: int, name: str = "main-store") -> ResponseStore:
    store = ResponseStore()
    store.project_id = project_id
    store.name = name
    store.store_type = "database"
    store.connection_reference = {"kind": "postgres"}
    store.created_by_user_id = user_id
    return store


def make_survey(project_id: int, response_store_id: int, user_id: int, title: str = "Customer Survey") -> Survey:
    survey = Survey()
    survey.project_id = project_id
    survey.title = title
    survey.default_response_store_id = response_store_id
    survey.created_by_user_id = user_id
    return survey


def make_survey_version(survey_id: int, user_id: int, version_number: int = 1, status: str = "draft") -> SurveyVersion:
    version = SurveyVersion()
    version.survey_id = survey_id
    version.version_number = version_number
    version.status = status
    version.created_by_user_id = user_id
    return version


@pytest.fixture
def user(app) -> User:
    user = make_user()
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def project(user: User) -> Project:
    project = make_project(user.id)
    db.session.add(project)
    db.session.commit()
    return project


@pytest.fixture
def project_role(project: Project) -> ProjectRole:
    role = make_project_role(project.id)
    db.session.add(role)
    db.session.commit()
    return role


@pytest.fixture
def response_store(project: Project, user: User) -> ResponseStore:
    store = make_response_store(project.id, user.id)
    db.session.add(store)
    db.session.commit()
    return store


@pytest.fixture
def survey(project: Project, response_store: ResponseStore, user: User) -> Survey:
    survey = make_survey(project.id, response_store.id, user.id)
    db.session.add(survey)
    db.session.commit()
    return survey


@pytest.fixture
def survey_version(survey: Survey, user: User) -> SurveyVersion:
    version = make_survey_version(survey.id, user.id)
    db.session.add(version)
    db.session.commit()
    return version


def test_user_unique_email(app):
    user_a = make_user(auth0_user_id="auth0|a", email="dup@example.com")
    db.session.add(user_a)
    db.session.commit()

    user_b = make_user(auth0_user_id="auth0|b", email="dup@example.com")
    db.session.add(user_b)

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_user_unique_auth0_user_id(app):
    user_a = make_user(auth0_user_id="auth0|same", email="one@example.com")
    db.session.add(user_a)
    db.session.commit()

    user_b = make_user(auth0_user_id="auth0|same", email="two@example.com")
    db.session.add(user_b)

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_project_unique_slug(app, user: User):
    project_a = make_project(user.id, name="One", slug="same")
    db.session.add(project_a)
    db.session.commit()

    project_b = make_project(user.id, name="Two", slug="same")
    db.session.add(project_b)

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_project_role_unique_name_within_project(project: Project):
    role_a = make_project_role(project.id, name="editor")
    db.session.add(role_a)
    db.session.commit()

    role_b = make_project_role(project.id, name="editor")
    db.session.add(role_b)

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_project_membership_unique_user_project(user: User, project: Project):
    membership_a = ProjectMembership()
    membership_a.user_id = user.id
    membership_a.project_id = project.id
    db.session.add(membership_a)
    db.session.commit()

    membership_b = ProjectMembership()
    membership_b.user_id = user.id
    membership_b.project_id = project.id
    db.session.add(membership_b)

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_response_store_unique_name_within_project(project: Project, user: User):
    store_a = ResponseStore()
    store_a.project_id = project.id
    store_a.name = "warehouse"
    store_a.store_type = "db"
    store_a.connection_reference = {"dsn": "x"}
    store_a.created_by_user_id = user.id
    db.session.add(store_a)
    db.session.commit()

    store_b = ResponseStore()
    store_b.project_id = project.id
    store_b.name = "warehouse"
    store_b.store_type = "db"
    store_b.connection_reference = {"dsn": "y"}
    store_b.created_by_user_id = user.id
    db.session.add(store_b)

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_response_subject_mapping_unique_project_user(project: Project, user: User):
    mapping_a = ResponseSubjectMapping()
    mapping_a.project_id = project.id
    mapping_a.user_id = user.id
    mapping_a.pseudonymous_subject_id = uuid.uuid4()
    db.session.add(mapping_a)
    db.session.commit()

    mapping_b = ResponseSubjectMapping()
    mapping_b.project_id = project.id
    mapping_b.user_id = user.id
    mapping_b.pseudonymous_subject_id = uuid.uuid4()
    db.session.add(mapping_b)

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_response_subject_mapping_unique_project_subject(project: Project, user: User):
    subject_id = uuid.uuid4()

    mapping_a = ResponseSubjectMapping()
    mapping_a.project_id = project.id
    mapping_a.user_id = user.id
    mapping_a.pseudonymous_subject_id = subject_id
    db.session.add(mapping_a)
    db.session.commit()

    other_user = make_user(auth0_user_id="auth0|u2", email="u2@example.com", display_name="U2")
    db.session.add(other_user)
    db.session.commit()

    mapping_b = ResponseSubjectMapping()
    mapping_b.project_id = project.id
    mapping_b.user_id = other_user.id
    mapping_b.pseudonymous_subject_id = subject_id
    db.session.add(mapping_b)

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_survey_version_unique_version_number_per_survey(survey: Survey, user: User):
    version_a = make_survey_version(survey.id, user.id, version_number=1)
    db.session.add(version_a)
    db.session.commit()

    version_b = make_survey_version(survey.id, user.id, version_number=1)
    db.session.add(version_b)

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_survey_public_link_unique_token_hash(survey: Survey):
    link_a = SurveyPublicLink()
    link_a.survey_id = survey.id
    link_a.token_prefix = "abc"
    link_a.token_hash = "hash-1"
    db.session.add(link_a)
    db.session.commit()

    link_b = SurveyPublicLink()
    link_b.survey_id = survey.id
    link_b.token_prefix = "def"
    link_b.token_hash = "hash-1"
    db.session.add(link_b)

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_survey_public_link_unique_prefix_within_survey(survey: Survey):
    link_a = SurveyPublicLink()
    link_a.survey_id = survey.id
    link_a.token_prefix = "same"
    link_a.token_hash = "hash-1"
    db.session.add(link_a)
    db.session.commit()

    link_b = SurveyPublicLink()
    link_b.survey_id = survey.id
    link_b.token_prefix = "same"
    link_b.token_hash = "hash-2"
    db.session.add(link_b)

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_submission_answer_unique_question_per_submission(app):
    submission = Submission()
    submission.core_submission_id = 999
    submission.survey_id = 1
    submission.survey_version_id = 1
    submission.project_id = 1
    submission.is_anonymous = False
    db.session.add(submission)
    db.session.commit()

    answer_a = SubmissionAnswer()
    answer_a.submission_id = submission.id
    answer_a.question_key = "q1"
    answer_a.answer_family = "text"
    answer_a.answer_value = {"value": "hello"}
    db.session.add(answer_a)
    db.session.commit()

    answer_b = SubmissionAnswer()
    answer_b.submission_id = submission.id
    answer_b.question_key = "q1"
    answer_b.answer_family = "text"
    answer_b.answer_value = {"value": "again"}
    db.session.add(answer_b)

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_submission_relationships_work(app):
    submission = Submission()
    submission.core_submission_id = 100
    submission.survey_id = 1
    submission.survey_version_id = 1
    submission.project_id = 1
    submission.is_anonymous = True

    answer = SubmissionAnswer()
    answer.question_key = "age"
    answer.answer_family = "number"
    answer.answer_value = {"value": 24}

    event = SubmissionEvent()
    event.event_type = "queued"
    event.event_payload = {"destination": "warehouse"}

    submission.answers.append(answer)
    submission.events.append(event)

    db.session.add(submission)
    db.session.commit()
    db.session.refresh(submission)

    assert len(submission.answers) == 1
    assert len(submission.events) == 1
    assert submission.answers[0].submission_id == submission.id
    assert submission.events[0].submission_id == submission.id


def test_submission_delete_cascades_answers_and_events(app):
    submission = Submission()
    submission.core_submission_id = 101
    submission.survey_id = 1
    submission.survey_version_id = 1
    submission.project_id = 1
    submission.is_anonymous = True

    answer = SubmissionAnswer()
    answer.question_key = "q1"
    answer.answer_family = "text"
    answer.answer_value = {"value": "x"}

    event = SubmissionEvent()
    event.event_type = "created"
    event.event_payload = {"ok": True}

    submission.answers.append(answer)
    submission.events.append(event)

    db.session.add(submission)
    db.session.commit()

    submission_id = submission.id
    answer_id = answer.id
    event_id = event.id

    db.session.delete(submission)
    db.session.commit()

    assert db.session.get(Submission, submission_id) is None
    assert db.session.get(SubmissionAnswer, answer_id) is None
    assert db.session.get(SubmissionEvent, event_id) is None


def test_survey_submission_can_be_created(
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
    db.session.add(submission)
    db.session.commit()

    saved = db.session.get(SurveySubmission, submission.id)
    assert saved is not None
    assert saved.submitted_by_user_id == user.id
    assert saved.submission_channel == "authenticated"
    assert saved.status == "pending"
