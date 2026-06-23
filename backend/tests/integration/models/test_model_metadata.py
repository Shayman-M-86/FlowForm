# tests/models/test_model_metadata.py
from __future__ import annotations

from sqlalchemy import ForeignKeyConstraint, UniqueConstraint, inspect
from sqlalchemy.orm import configure_mappers

from app.schema.orm.core import (
    AuditLog,
    Project,
    ProjectMembership,
    ProjectRole,
    ProjectSubject,
    ProjectSubjectIdentity,
    ProjectSubjectToken,
    ResponseStore,
    SubmissionEvent,
    SubmissionSession,
    Survey,
    SurveyLink,
    SurveyMembershipRole,
    SurveyQuestion,
    SurveyRole,
    SurveyScoringRule,
    SurveyVersion,
    User,
    project_role_permissions,
    survey_role_permissions,
)
from app.schema.orm.response import ResponseAnswer, ResponseAnswerRevision, ResponseEnvelope


def get_relationship(model, name: str):
    return inspect(model).relationships[name]


def unique_constraint_names(model) -> set[str]:
    names: set[str] = set()
    for constraint in model.__table__.constraints:
        if isinstance(constraint, UniqueConstraint) and isinstance(constraint.name, str):
            names.add(constraint.name)
    return names


def foreign_key_constraint_names(model) -> set[str]:
    names: set[str] = set()
    for constraint in model.__table__.constraints:
        if isinstance(constraint, ForeignKeyConstraint) and isinstance(constraint.name, str):
            names.add(constraint.name)
    return names


def index_names(model) -> set[str]:
    names: set[str] = set()
    for index in model.__table__.indexes:
        if isinstance(index.name, str):
            names.add(index.name)
    return names


def test_all_mappers_configure() -> None:
    configure_mappers()


# -------------------------
# Relationship wiring
# -------------------------


def test_audit_log_relationships() -> None:
    assert get_relationship(AuditLog, "user").mapper.class_ is User


def test_project_relationships() -> None:
    assert get_relationship(Project, "created_by").mapper.class_ is User


def test_project_role_relationships() -> None:
    assert get_relationship(ProjectRole, "permissions").secondary is project_role_permissions


def test_project_membership_relationships() -> None:
    assert get_relationship(ProjectMembership, "user").mapper.class_ is User
    assert get_relationship(ProjectMembership, "project").mapper.class_ is Project
    assert get_relationship(ProjectMembership, "role").mapper.class_ is ProjectRole


def test_response_store_relationships() -> None:
    assert get_relationship(ResponseStore, "project").mapper.class_ is Project
    assert get_relationship(ResponseStore, "created_by").mapper.class_ is User


def test_project_subject_relationships() -> None:
    assert get_relationship(ProjectSubject, "project").mapper.class_ is Project
    assert get_relationship(ProjectSubject, "identities").mapper.class_ is ProjectSubjectIdentity
    assert get_relationship(ProjectSubject, "tokens").mapper.class_ is ProjectSubjectToken
    assert get_relationship(ProjectSubjectIdentity, "subject").mapper.class_ is ProjectSubject
    assert get_relationship(ProjectSubjectIdentity, "user").mapper.class_ is User
    assert get_relationship(ProjectSubjectToken, "subject").mapper.class_ is ProjectSubject


def test_survey_relationships() -> None:
    assert get_relationship(Survey, "versions").mapper.class_ is SurveyVersion
    assert get_relationship(Survey, "published_version").mapper.class_ is SurveyVersion
    assert get_relationship(Survey, "created_by").mapper.class_ is User


def test_survey_version_relationships() -> None:
    assert get_relationship(SurveyVersion, "survey").mapper.class_ is Survey
    assert get_relationship(SurveyVersion, "created_by").mapper.class_ is User


def test_survey_content_relationships() -> None:
    assert get_relationship(SurveyQuestion, "survey_version").mapper.class_ is SurveyVersion
    assert get_relationship(SurveyScoringRule, "survey_version").mapper.class_ is SurveyVersion


def test_survey_role_relationships() -> None:
    assert get_relationship(SurveyRole, "permissions").secondary is survey_role_permissions


def test_survey_link_relationships() -> None:
    assert get_relationship(SurveyLink, "survey").mapper.class_ is Survey


def test_submission_session_relationships() -> None:
    assert get_relationship(SubmissionSession, "project_subject").mapper.class_ is ProjectSubject
    assert get_relationship(SubmissionSession, "response_store").mapper.class_ is ResponseStore
    assert get_relationship(SubmissionSession, "survey").mapper.class_ is Survey
    assert get_relationship(SubmissionSession, "survey_version").mapper.class_ is SurveyVersion
    assert get_relationship(SubmissionSession, "link").mapper.class_ is SurveyLink
    assert get_relationship(SubmissionEvent, "session").mapper.class_ is SubmissionSession
    assert get_relationship(SubmissionEvent, "question").mapper.class_ is SurveyQuestion


def test_response_relationships() -> None:
    assert get_relationship(ResponseEnvelope, "answers").mapper.class_ is ResponseAnswer
    assert get_relationship(ResponseAnswer, "envelope").mapper.class_ is ResponseEnvelope
    assert get_relationship(ResponseAnswer, "revisions").mapper.class_ is ResponseAnswerRevision
    assert get_relationship(ResponseAnswer, "latest_revision").mapper.class_ is ResponseAnswerRevision
    assert get_relationship(ResponseAnswerRevision, "answer").mapper.class_ is ResponseAnswer


# -------------------------
# Foreign key constraint presence
# -------------------------


def test_project_membership_foreign_keys() -> None:
    names = foreign_key_constraint_names(ProjectMembership)

    assert "fk_project_memberships_role_id__project_roles" in names, (
        f"Missing FK constraint: 'fk_project_memberships_role_id__project_roles'. Found: {sorted(names)}"
    )

    assert "fk_project_memberships_role_same_project" in names, (
        f"Missing composite FK constraint: 'fk_project_memberships_role_same_project'. Found: {sorted(names)}"
    )


def test_response_store_foreign_keys() -> None:
    names = foreign_key_constraint_names(ResponseStore)
    assert "fk_response_stores_project_id__projects" in names


def test_survey_foreign_keys() -> None:
    names = foreign_key_constraint_names(Survey)
    assert "fk_surveys_default_store" in names
    assert "fk_surveys_default_store_same_project" in names
    assert "fk_surveys_published_version_same_survey" in names


def test_survey_membership_role_foreign_keys() -> None:
    names = foreign_key_constraint_names(SurveyMembershipRole)
    assert "fk_survey_membership_roles_survey_same_project" in names
    assert "fk_survey_membership_roles_membership_same_project" in names
    assert "fk_survey_membership_roles_role_same_project" in names


def test_submission_session_foreign_keys() -> None:
    names = foreign_key_constraint_names(SubmissionSession)
    assert "fk_submission_sessions_survey_same_project" in names
    assert "fk_submission_sessions_version_same_survey" in names
    assert "fk_submission_sessions_store_same_project" in names
    assert "fk_submission_sessions_link_same_survey" in names
    assert "fk_submission_sessions_project_subject_same_project" in names


# -------------------------
# Important named unique/index constraints
# -------------------------


def test_project_membership_unique_constraints() -> None:
    names = unique_constraint_names(ProjectMembership)
    assert "uq_project_memberships_project_id_id" in names


def test_project_subject_unique_constraints() -> None:
    assert "uq_project_subjects_project_id_id" in unique_constraint_names(ProjectSubject)


def test_project_subject_identity_foreign_keys() -> None:
    names = foreign_key_constraint_names(ProjectSubjectIdentity)
    assert "fk_project_subject_identities_subject_same_project" in names
    assert "fk_project_subject_identities_user_email_matches" in names


def test_project_subject_identity_unique_constraints() -> None:
    assert "uq_project_subject_identities_project_subject_id" in unique_constraint_names(ProjectSubjectIdentity)


def test_user_unique_constraints() -> None:
    assert "uq_users_id_email" in unique_constraint_names(User)


def test_survey_version_constraints() -> None:
    names = unique_constraint_names(SurveyVersion)
    assert "uq_survey_versions_survey_id_id" in names


def test_survey_content_unique_constraints() -> None:
    assert "uq_survey_questions_survey_version_id_id" in unique_constraint_names(SurveyQuestion)


def test_survey_role_unique_constraints() -> None:
    names = unique_constraint_names(SurveyRole)
    assert "uq_survey_roles_project_id_id" in names


def test_survey_link_unique_constraints() -> None:
    names = unique_constraint_names(SurveyLink)
    assert "uq_survey_links_token" in names
    assert "uq_survey_links_survey_id_id" in names


def test_submission_session_unique_constraints() -> None:
    names = unique_constraint_names(SubmissionSession)
    assert "uq_submission_sessions_id_survey_version_id" in names
    assert "uq_submission_sessions_project_id_id" in names
    assert "uq_submission_sessions_id_project_subject_id" in names


def test_response_answer_unique_constraints() -> None:
    names = unique_constraint_names(ResponseAnswer)
    assert "uq_response_answers_id_envelope_id" in names
    assert "uq_response_answers_envelope_id_answer_locator" in names


def test_response_answer_revision_unique_constraints() -> None:
    names = unique_constraint_names(ResponseAnswerRevision)
    assert "uq_response_answer_revisions_id_answer_id" in names
    assert "uq_response_answer_revisions_answer_id_revision_number" in names
    assert "uq_response_answer_revisions_envelope_id_nonce" in names
    assert "uq_response_answer_revisions_answer_id_client_mutation_id" in names


# -------------------------
# Join table sanity checks
# -------------------------


def test_project_role_permissions_join_table_shape() -> None:
    table = project_role_permissions
    assert set(table.c.keys()) == {"role_id", "permission_id"}
    assert table.c["role_id"].primary_key is True
    assert table.c["permission_id"].primary_key is True


def test_survey_role_permissions_join_table_shape() -> None:
    table = survey_role_permissions
    assert set(table.c.keys()) == {"role_id", "permission_id"}
    assert table.c["role_id"].primary_key is True
    assert table.c["permission_id"].primary_key is True
