from __future__ import annotations

import hashlib
import random
import secrets
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
from app.models.response.submission import Submission
from app.models.response.submission_answer import SubmissionAnswer
from app.models.response.submission_event import SubmissionEvent


def make_token_pair() -> tuple[str, str, str]:
    token = secrets.token_urlsafe(32)
    token_prefix = token[:8]
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, token_prefix, token_hash


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
    store.store_type = "platform_postgres"
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


def make_core_submission_id() -> int:
    return random.randint(1, 2**63 - 1)


def make_submission() -> Submission:
    submission = Submission()
    submission.core_submission_id = make_core_submission_id()
    submission.survey_id = 1
    submission.survey_version_id = 1
    submission.project_id = 1
    submission.is_anonymous = False
    return submission


def make_answer(
    submission_id: int,
    *,
    question_key: str = "q1",
    answer_family: str = "choice",
    answer_value: dict | None = None,
) -> SubmissionAnswer:
    answer = SubmissionAnswer()
    answer.submission_id = submission_id
    answer.question_key = question_key
    answer.answer_family = answer_family
    answer.answer_value = answer_value or {"selected_option_ids": ["opt1"]}
    return answer


def make_event(
    submission_id: int,
    *,
    event_type: str = "queued",
    event_payload: dict | None = None,
) -> SubmissionEvent:
    event = SubmissionEvent()
    event.submission_id = submission_id
    event.event_type = event_type
    event.event_payload = event_payload or {"destination": "warehouse"}
    return event


@pytest.fixture
def user(db_session: scoped_session[Session]) -> User:
    user = make_user()
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def project(user: User, db_session: scoped_session[Session]) -> Project:
    project = make_project(user.id)
    db_session.add(project)
    db_session.flush()
    return project


@pytest.fixture
def project_role(project: Project, db_session: scoped_session[Session]) -> ProjectRole:
    role = make_project_role(project.id)
    db_session.add(role)
    db_session.flush()
    return role


@pytest.fixture
def response_store(project: Project, user: User, db_session: scoped_session[Session]) -> ResponseStore:
    store = make_response_store(project.id, user.id)
    db_session.add(store)
    db_session.flush()
    return store


@pytest.fixture
def survey(project: Project, response_store: ResponseStore, user: User, db_session: scoped_session[Session]) -> Survey:
    survey = make_survey(project.id, response_store.id, user.id)
    db_session.add(survey)
    db_session.flush()
    return survey


@pytest.fixture
def survey_version(survey: Survey, user: User, db_session: scoped_session[Session]) -> SurveyVersion:
    version = make_survey_version(survey.id, user.id)
    db_session.add(version)
    db_session.flush()
    return version


def test_user_unique_email(db_session: scoped_session[Session]):
    user_a = make_user(auth0_user_id="auth0|a", email="dup@example.com")
    db_session.add(user_a)
    db_session.flush()

    user_b = make_user(auth0_user_id="auth0|b", email="dup@example.com")
    db_session.add(user_b)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_user_unique_auth0_user_id(db_session: scoped_session[Session]):
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


def test_project_role_unique_name_within_project(project: Project, db_session: scoped_session[Session]):
    role_a = make_project_role(project.id, name="editor")
    db_session.add(role_a)
    db_session.flush()

    role_b = make_project_role(project.id, name="editor")
    db_session.add(role_b)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_project_membership_unique_user_project(user: User, project: Project, db_session: scoped_session[Session]):
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


def test_response_store_unique_name_within_project(project: Project, user: User, db_session: scoped_session[Session]):
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
    project: Project, user: User, db_session: scoped_session[Session]
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
    project: Project, user: User, db_session: scoped_session[Session]
):
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

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_survey_version_unique_version_number_per_survey(
    survey: Survey, user: User, db_session: scoped_session[Session]
):
    version_a = make_survey_version(survey.id, user.id, version_number=1)
    db_session.add(version_a)
    db_session.flush()

    version_b = make_survey_version(survey.id, user.id, version_number=1)
    db_session.add(version_b)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_survey_public_link_unique_token_hash(survey: Survey, db_session: scoped_session[Session]):
    _, prefix, hash_a = make_token_pair()

    link_a = SurveyPublicLink()
    link_a.survey_id = survey.id
    link_a.token_prefix = prefix
    link_a.token_hash = hash_a
    db_session.add(link_a)
    db_session.flush()

    _, _, hash_b = make_token_pair()

    link_b = SurveyPublicLink()
    link_b.survey_id = survey.id
    link_b.token_prefix = prefix
    link_b.token_hash = hash_b
    db_session.add(link_b)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_survey_public_link_unique_prefix_within_survey(survey: Survey, db_session: scoped_session[Session]):
    _, token_prefix, token_hash = make_token_pair()

    link_a = SurveyPublicLink()
    link_a.survey_id = survey.id
    link_a.token_prefix = token_prefix
    link_a.token_hash = token_hash
    db_session.add(link_a)
    db_session.flush()

    link_b = SurveyPublicLink()
    link_b.survey_id = survey.id
    link_b.token_prefix = token_prefix
    link_b.token_hash = token_hash
    db_session.add(link_b)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_submission_answer_unique_question_per_submission(
    db_session: scoped_session[Session],
) -> None:
    submission = make_submission()
    db_session.add(submission)
    db_session.flush()

    answer_a = make_answer(
        submission.id,
        question_key="q1",
        answer_family="choice",
        answer_value={"selected_option_ids": ["opt1"]},
    )
    db_session.add(answer_a)
    db_session.flush()

    answer_b = make_answer(
        submission.id,
        question_key="q1",  # duplicate within same submission
        answer_family="choice",
        answer_value={"selected_option_ids": ["opt2"]},
    )
    db_session.add(answer_b)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_submission_allows_different_question_keys_within_same_submission(
    db_session: scoped_session[Session],
) -> None:
    submission = make_submission()
    db_session.add(submission)
    db_session.flush()

    answer_a = make_answer(submission.id, question_key="q1", answer_family="choice")
    answer_b = make_answer(submission.id, question_key="q2", answer_family="choice")

    db_session.add_all([answer_a, answer_b])
    db_session.flush()

    saved_answers = db_session.query(SubmissionAnswer).filter_by(submission_id=submission.id).all()
    assert len(saved_answers) == 2


def test_submission_allows_same_question_key_across_different_submissions(
    db_session: scoped_session[Session],
) -> None:
    submission_a = make_submission()
    submission_b = make_submission()
    db_session.add_all([submission_a, submission_b])
    db_session.flush()

    answer_a = make_answer(submission_a.id, question_key="q1", answer_family="choice")
    answer_b = make_answer(submission_b.id, question_key="q1", answer_family="choice")

    db_session.add_all([answer_a, answer_b])
    db_session.flush()

    assert answer_a.submission_id != answer_b.submission_id


def test_submission_relationships_answers_work(
    db_session: scoped_session[Session],
) -> None:
    submission = make_submission()

    answer = SubmissionAnswer()
    answer.question_key = "age"
    answer.answer_family = "choice"
    answer.answer_value = {"selected_option_ids": ["a1"]}

    submission.answers.append(answer)

    db_session.add(submission)
    db_session.flush()
    db_session.refresh(submission)

    assert len(submission.answers) == 1
    assert submission.answers[0].submission_id == submission.id
    assert submission.answers[0].question_key == "age"


def test_submission_relationships_events_work(
    db_session: scoped_session[Session],
) -> None:
    submission = make_submission()

    event = SubmissionEvent()
    event.event_type = "queued"
    event.event_payload = {"destination": "warehouse"}

    submission.events.append(event)

    db_session.add(submission)
    db_session.flush()
    db_session.refresh(submission)

    assert len(submission.events) == 1
    assert submission.events[0].submission_id == submission.id
    assert submission.events[0].event_type == "queued"


def test_survey_submission_can_be_created(
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
    user: User,
    db_session: scoped_session[Session],
) -> None:
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


def test_survey_submission_requires_survey_version(
    project: Project,
    survey: Survey,
    response_store: ResponseStore,
    user: User,
    db_session: scoped_session[Session],
) -> None:
    submission = SurveySubmission()
    submission.project_id = project.id
    submission.survey_id = survey.id
    submission.response_store_id = response_store.id
    submission.submission_channel = "authenticated"
    submission.submitted_by_user_id = user.id
    submission.status = "pending"
    submission.is_anonymous = False

    db_session.add(submission)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_survey_submission_requires_submission_channel(
    project: Project,
    survey: Survey,
    survey_version: SurveyVersion,
    response_store: ResponseStore,
    user: User,
    db_session: scoped_session[Session],
) -> None:
    submission = SurveySubmission()
    submission.project_id = project.id
    submission.survey_id = survey.id
    submission.survey_version_id = survey_version.id
    submission.response_store_id = response_store.id
    submission.submitted_by_user_id = user.id
    submission.status = "pending"
    submission.is_anonymous = False

    db_session.add(submission)
    

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()
