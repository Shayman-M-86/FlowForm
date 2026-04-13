# tests/models/test_model_metadata.py
from __future__ import annotations

from sqlalchemy import ForeignKeyConstraint, UniqueConstraint, inspect
from sqlalchemy.orm import configure_mappers

from app.schema.orm.core import (
    AuditLog,
    Project,
    ProjectMembership,
    ProjectRole,
    ResponseStore,
    ResponseSubjectMapping,
    Survey,
    SurveyLink,
    SurveyMembershipRole,
    SurveyQuestion,
    SurveyRole,
    SurveyRule,
    SurveyScoringRule,
    SurveySubmission,
    SurveyVersion,
    User,
    project_role_permissions,
    survey_role_permissions,
)
from app.schema.orm.response import Submission, SubmissionAnswer, SubmissionEvent


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


def test_response_subject_mapping_relationships() -> None:
    assert get_relationship(ResponseSubjectMapping, "project").mapper.class_ is Project
    assert get_relationship(ResponseSubjectMapping, "user").mapper.class_ is User


def test_survey_relationships() -> None:
    assert get_relationship(Survey, "versions").mapper.class_ is SurveyVersion
    assert get_relationship(Survey, "published_version").mapper.class_ is SurveyVersion
    assert get_relationship(Survey, "created_by").mapper.class_ is User


def test_survey_version_relationships() -> None:
    assert get_relationship(SurveyVersion, "survey").mapper.class_ is Survey
    assert get_relationship(SurveyVersion, "created_by").mapper.class_ is User


def test_survey_content_relationships() -> None:
    assert get_relationship(SurveyQuestion, "survey_version").mapper.class_ is SurveyVersion
    assert get_relationship(SurveyRule, "survey_version").mapper.class_ is SurveyVersion
    assert get_relationship(SurveyScoringRule, "survey_version").mapper.class_ is SurveyVersion


def test_survey_role_relationships() -> None:
    assert get_relationship(SurveyRole, "permissions").secondary is survey_role_permissions


def test_survey_link_relationships() -> None:
    assert get_relationship(SurveyLink, "survey").mapper.class_ is Survey


def test_survey_submission_relationships() -> None:
    assert get_relationship(SurveySubmission, "submitted_by").mapper.class_ is User


def test_response_relationships() -> None:
    assert get_relationship(Submission, "answers").mapper.class_ is SubmissionAnswer
    assert get_relationship(Submission, "events").mapper.class_ is SubmissionEvent
    assert get_relationship(SubmissionAnswer, "submission").mapper.class_ is Submission
    assert get_relationship(SubmissionEvent, "submission").mapper.class_ is Submission


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


def test_survey_submission_foreign_keys() -> None:
    names = foreign_key_constraint_names(SurveySubmission)
    assert "fk_survey_submissions_survey_same_project" in names
    assert "fk_survey_submissions_version_same_survey" in names
    assert "fk_survey_submissions_store" in names
    assert "fk_survey_submissions_store_same_project" in names
    assert "fk_survey_submissions_survey_link" in names
    assert "fk_survey_submissions_survey_link_same_survey" in names
    assert "fk_survey_submissions_subject_same_project" in names


# -------------------------
# Important named unique/index constraints
# -------------------------


def test_project_membership_unique_constraints() -> None:
    names = unique_constraint_names(ProjectMembership)
    assert "uq_project_memberships_user_project" in names 
    assert "uq_project_memberships_project_id_id" in names


def test_response_subject_mapping_unique_constraints() -> None:
    names = unique_constraint_names(ResponseSubjectMapping)
    assert "uq_response_subject_mappings_project_id_id" in names
    assert "uq_response_subject_mappings_project_id_user_id" in names
    assert "uq_response_subject_mappings_project_id_pseudonymous_subject_id" in names


def test_survey_version_constraints() -> None:
    names = unique_constraint_names(SurveyVersion)
    assert "uq_survey_versions_survey_id_id" in names
    assert "uq_survey_versions_survey_id_version_number" in names
    assert "uq_survey_versions_one_published" in index_names(SurveyVersion)


def test_survey_content_unique_constraints() -> None:
    assert "uq_survey_questions_survey_version_id_question_key" in unique_constraint_names(SurveyQuestion)
    assert "uq_survey_rules_survey_version_id_rule_key" in unique_constraint_names(SurveyRule)
    assert "uq_survey_scoring_rules_survey_version_id_scoring_key" in unique_constraint_names(SurveyScoringRule)


def test_survey_role_unique_constraints() -> None:
    names = unique_constraint_names(SurveyRole)
    assert "uq_survey_roles_project_id_id" in names
    assert "uq_survey_roles_project_id_name" in names


def test_survey_link_unique_constraints() -> None:
    names = unique_constraint_names(SurveyLink)
    assert "uq_survey_links_token_hash" in names
    assert "uq_survey_links_survey_id_id" in names
    assert "uq_survey_links_survey_id_token_prefix" in names


def test_survey_submission_indexes() -> None:
    assert "uq_survey_submissions_external_submission_id" in index_names(SurveySubmission)


def test_submission_answer_unique_constraints() -> None:
    assert "uq_submission_answers_question" in unique_constraint_names(SubmissionAnswer)


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
