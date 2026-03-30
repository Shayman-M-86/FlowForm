# tests/models/test_model_metadata.py
from __future__ import annotations

from sqlalchemy import ForeignKeyConstraint, UniqueConstraint, inspect
from sqlalchemy.orm import configure_mappers

from app.models.core.audit_log import AuditLog
from app.models.core.permission import Permission
from app.models.core.project import (
    Project,
    ProjectMembership,
    ProjectRole,
    project_role_permissions,
)
from app.models.core.response_store import ResponseStore
from app.models.core.response_subject_mapping import ResponseSubjectMapping
from app.models.core.survey import Survey, SurveyVersion
from app.models.core.survey_access import (
    SurveyMembershipRole,
    SurveyPublicLink,
    SurveyRole,
    survey_role_permissions,
)
from app.models.core.survey_content import (
    SurveyQuestion,
    SurveyRule,
    SurveyScoringRule,
)
from app.models.core.survey_submission import SurveySubmission
from app.models.core.user import User
from app.models.response.submission import Submission
from app.models.response.submission_answer import SubmissionAnswer
from app.models.response.submission_event import SubmissionEvent


def get_column(model, name: str):
    return model.__table__.c[name]


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


def test_all_mappers_configure():
    configure_mappers()


# -------------------------
# User / Permission / Audit
# -------------------------


def test_user_table_shape():
    assert User.__tablename__ == "users"

    assert get_column(User, "id").primary_key is True
    assert get_column(User, "auth0_user_id").nullable is False
    assert get_column(User, "email").nullable is False
    assert get_column(User, "display_name").nullable is True
    assert get_column(User, "created_at").nullable is False

    assert get_column(User, "auth0_user_id").unique is True
    assert get_column(User, "email").unique is True


def test_permission_table_shape():
    assert Permission.__tablename__ == "permissions"

    assert get_column(Permission, "id").primary_key is True
    assert get_column(Permission, "name").nullable is False
    assert get_column(Permission, "name").unique is True


def test_audit_log_table_shape():
    assert AuditLog.__tablename__ == "audit_logs"

    assert get_column(AuditLog, "id").primary_key is True
    assert get_column(AuditLog, "user_id").nullable is True
    assert get_column(AuditLog, "action").nullable is False
    assert get_column(AuditLog, "entity_type").nullable is False
    assert get_column(AuditLog, "entity_id").nullable is True
    assert get_column(AuditLog, "metadata").nullable is True
    assert get_column(AuditLog, "created_at").nullable is False

    rel = get_relationship(AuditLog, "user")
    assert rel.mapper.class_ is User


# -------------------------
# Project models
# -------------------------


def test_project_table_shape():
    assert Project.__tablename__ == "projects"

    assert get_column(Project, "id").primary_key is True
    assert get_column(Project, "name").nullable is False
    assert get_column(Project, "slug").nullable is False
    assert get_column(Project, "slug").unique is True
    assert get_column(Project, "created_by_user_id").nullable is True
    assert get_column(Project, "created_at").nullable is False

    rel = get_relationship(Project, "created_by")
    assert rel.mapper.class_ is User


def test_project_role_table_shape():
    assert ProjectRole.__tablename__ == "project_roles"

    assert get_column(ProjectRole, "id").primary_key is True
    assert get_column(ProjectRole, "project_id").nullable is False
    assert get_column(ProjectRole, "name").nullable is False
    assert get_column(ProjectRole, "is_system_role").nullable is False
    assert get_column(ProjectRole, "created_at").nullable is False

    assert "uq_project_roles_project_id" in unique_constraint_names(ProjectRole)
    assert "uq_project_roles_project_name" in unique_constraint_names(ProjectRole)

    rel = get_relationship(ProjectRole, "permissions")
    assert rel.secondary is project_role_permissions


def test_project_membership_table_shape():
    assert ProjectMembership.__tablename__ == "project_memberships"

    assert get_column(ProjectMembership, "id").primary_key is True
    assert get_column(ProjectMembership, "user_id").nullable is False
    assert get_column(ProjectMembership, "project_id").nullable is False
    assert get_column(ProjectMembership, "role_id").nullable is True
    assert get_column(ProjectMembership, "status").nullable is False
    assert get_column(ProjectMembership, "created_at").nullable is False

    assert "uq_project_memberships_user_project" in unique_constraint_names(ProjectMembership)
    assert "uq_project_memberships_project_id" in unique_constraint_names(ProjectMembership)
    assert "fk_project_memberships_role" in foreign_key_constraint_names(ProjectMembership)
    assert "fk_project_memberships_role_same_project" in foreign_key_constraint_names(ProjectMembership)

    assert get_relationship(ProjectMembership, "user").mapper.class_ is User
    assert get_relationship(ProjectMembership, "project").mapper.class_ is Project
    assert get_relationship(ProjectMembership, "role").mapper.class_ is ProjectRole


def test_project_role_permissions_join_table_shape():
    table = project_role_permissions

    assert table.name == "project_role_permissions"
    assert set(table.c.keys()) == {"role_id", "permission_id"}
    assert table.c["role_id"].primary_key is True
    assert table.c["permission_id"].primary_key is True


# -------------------------
# Response store / subject mapping
# -------------------------


def test_response_store_table_shape():
    assert ResponseStore.__tablename__ == "response_stores"

    assert get_column(ResponseStore, "id").primary_key is True
    assert get_column(ResponseStore, "project_id").nullable is False
    assert get_column(ResponseStore, "name").nullable is False
    assert get_column(ResponseStore, "store_type").nullable is False
    assert get_column(ResponseStore, "connection_reference").nullable is False
    assert get_column(ResponseStore, "is_active").nullable is False
    assert get_column(ResponseStore, "created_by_user_id").nullable is True

    assert "uq_response_stores_project_id" in unique_constraint_names(ResponseStore)
    assert "uq_response_stores_project_name" in unique_constraint_names(ResponseStore)
    assert "fk_response_stores_project" in foreign_key_constraint_names(ResponseStore)

    assert get_relationship(ResponseStore, "project").mapper.class_ is Project
    assert get_relationship(ResponseStore, "created_by").mapper.class_ is User


def test_response_subject_mapping_table_shape():
    assert ResponseSubjectMapping.__tablename__ == "response_subject_mappings"

    assert get_column(ResponseSubjectMapping, "id").primary_key is True
    assert get_column(ResponseSubjectMapping, "project_id").nullable is False
    assert get_column(ResponseSubjectMapping, "user_id").nullable is False
    assert get_column(ResponseSubjectMapping, "pseudonymous_subject_id").nullable is False
    assert get_column(ResponseSubjectMapping, "created_at").nullable is False

    names = unique_constraint_names(ResponseSubjectMapping)
    assert "uq_response_subject_mappings_project_id" in names
    assert "uq_response_subject_mappings_project_user" in names
    assert "uq_response_subject_mappings_project_subject" in names

    assert get_relationship(ResponseSubjectMapping, "project").mapper.class_ is Project
    assert get_relationship(ResponseSubjectMapping, "user").mapper.class_ is User


# -------------------------
# Survey core
# -------------------------


def test_survey_table_shape():
    assert Survey.__tablename__ == "surveys"

    assert get_column(Survey, "id").primary_key is True
    assert get_column(Survey, "project_id").nullable is False
    assert get_column(Survey, "title").nullable is False
    assert get_column(Survey, "visibility").nullable is False
    assert get_column(Survey, "allow_public_responses").nullable is False
    assert get_column(Survey, "public_slug").nullable is True
    assert get_column(Survey, "default_response_store_id").nullable is True
    assert get_column(Survey, "published_version_id").nullable is True
    assert get_column(Survey, "created_by_user_id").nullable is True

    assert get_column(Survey, "public_slug").unique is True
    assert "uq_surveys_project_id" in unique_constraint_names(Survey)

    fk_names = foreign_key_constraint_names(Survey)
    assert "fk_surveys_default_store" in fk_names
    assert "fk_surveys_default_store_same_project" in fk_names
    assert "fk_surveys_published_version_same_survey" in fk_names

    assert get_relationship(Survey, "versions").mapper.class_ is SurveyVersion
    assert get_relationship(Survey, "published_version").mapper.class_ is SurveyVersion
    assert get_relationship(Survey, "created_by").mapper.class_ is User


def test_survey_version_table_shape():
    assert SurveyVersion.__tablename__ == "survey_versions"

    assert get_column(SurveyVersion, "id").primary_key is True
    assert get_column(SurveyVersion, "survey_id").nullable is False
    assert get_column(SurveyVersion, "version_number").nullable is False
    assert get_column(SurveyVersion, "status").nullable is False
    assert get_column(SurveyVersion, "compiled_schema").nullable is True
    assert get_column(SurveyVersion, "published_at").nullable is True
    assert get_column(SurveyVersion, "created_by_user_id").nullable is True
    assert get_column(SurveyVersion, "deleted_at").nullable is True

    names = unique_constraint_names(SurveyVersion)
    assert "uq_survey_versions_survey_id" in names
    assert "uq_survey_versions_version_number" in names

    idx_names = index_names(SurveyVersion)
    assert "uq_survey_versions_one_published" in idx_names

    assert get_relationship(SurveyVersion, "survey").mapper.class_ is Survey
    assert get_relationship(SurveyVersion, "created_by").mapper.class_ is User


# -------------------------
# Survey content
# -------------------------


def test_survey_question_table_shape():
    assert SurveyQuestion.__tablename__ == "survey_questions"

    assert get_column(SurveyQuestion, "id").primary_key is True
    assert get_column(SurveyQuestion, "survey_version_id").nullable is False
    assert get_column(SurveyQuestion, "question_key").nullable is False
    assert get_column(SurveyQuestion, "question_schema").nullable is False

    assert "uq_survey_questions_version_key" in unique_constraint_names(SurveyQuestion)
    assert get_relationship(SurveyQuestion, "survey_version").mapper.class_ is SurveyVersion


def test_survey_rule_table_shape():
    assert SurveyRule.__tablename__ == "survey_rules"

    assert get_column(SurveyRule, "id").primary_key is True
    assert get_column(SurveyRule, "survey_version_id").nullable is False
    assert get_column(SurveyRule, "rule_key").nullable is False
    assert get_column(SurveyRule, "rule_schema").nullable is False

    assert "uq_survey_rules_version_key" in unique_constraint_names(SurveyRule)
    assert get_relationship(SurveyRule, "survey_version").mapper.class_ is SurveyVersion


def test_survey_scoring_rule_table_shape():
    assert SurveyScoringRule.__tablename__ == "survey_scoring_rules"

    assert get_column(SurveyScoringRule, "id").primary_key is True
    assert get_column(SurveyScoringRule, "survey_version_id").nullable is False
    assert get_column(SurveyScoringRule, "scoring_key").nullable is False
    assert get_column(SurveyScoringRule, "scoring_schema").nullable is False

    assert "uq_survey_scoring_rules_version_key" in unique_constraint_names(SurveyScoringRule)
    assert get_relationship(SurveyScoringRule, "survey_version").mapper.class_ is SurveyVersion


# -------------------------
# Survey access
# -------------------------


def test_survey_role_table_shape():
    assert SurveyRole.__tablename__ == "survey_roles"

    assert get_column(SurveyRole, "id").primary_key is True
    assert get_column(SurveyRole, "project_id").nullable is False
    assert get_column(SurveyRole, "name").nullable is False
    assert get_column(SurveyRole, "created_at").nullable is False

    assert "uq_survey_roles_project_id" in unique_constraint_names(SurveyRole)
    assert "uq_survey_roles_project_name" in unique_constraint_names(SurveyRole)

    rel = get_relationship(SurveyRole, "permissions")
    assert rel.secondary is survey_role_permissions


def test_survey_membership_role_table_shape():
    assert SurveyMembershipRole.__tablename__ == "survey_membership_roles"

    assert get_column(SurveyMembershipRole, "project_id").nullable is False
    assert get_column(SurveyMembershipRole, "survey_id").primary_key is True
    assert get_column(SurveyMembershipRole, "membership_id").primary_key is True
    assert get_column(SurveyMembershipRole, "role_id").nullable is False
    assert get_column(SurveyMembershipRole, "created_at").nullable is False

    fk_names = foreign_key_constraint_names(SurveyMembershipRole)
    assert "fk_survey_membership_roles_survey_same_project" in fk_names
    assert "fk_survey_membership_roles_membership_same_project" in fk_names
    assert "fk_survey_membership_roles_role_same_project" in fk_names


def test_survey_public_link_table_shape():
    assert SurveyPublicLink.__tablename__ == "survey_public_links"

    assert get_column(SurveyPublicLink, "id").primary_key is True
    assert get_column(SurveyPublicLink, "survey_id").nullable is False
    assert get_column(SurveyPublicLink, "token_prefix").nullable is False
    assert get_column(SurveyPublicLink, "token_hash").nullable is False
    assert get_column(SurveyPublicLink, "token_hash").unique is True
    assert get_column(SurveyPublicLink, "is_active").nullable is False
    assert get_column(SurveyPublicLink, "allow_response").nullable is False
    assert get_column(SurveyPublicLink, "expires_at").nullable is True
    assert get_column(SurveyPublicLink, "created_at").nullable is False

    assert "uq_survey_public_links_survey_id" in unique_constraint_names(SurveyPublicLink)
    assert "uq_survey_public_links_prefix" in unique_constraint_names(SurveyPublicLink)

    assert get_relationship(SurveyPublicLink, "survey").mapper.class_ is Survey


# -------------------------
# Survey submission
# -------------------------


def test_survey_submission_table_shape():
    assert SurveySubmission.__tablename__ == "survey_submissions"

    required_columns = [
        "id",
        "project_id",
        "survey_id",
        "survey_version_id",
        "response_store_id",
        "submission_channel",
        "status",
        "is_anonymous",
        "created_at",
    ]
    for name in required_columns:
        assert get_column(SurveySubmission, name).nullable is False

    nullable_columns = [
        "submitted_by_user_id",
        "public_link_id",
        "pseudonymous_subject_id",
        "external_submission_id",
        "started_at",
        "submitted_at",
        "last_delivery_attempt_at",
        "delivery_error",
    ]
    for name in nullable_columns:
        assert get_column(SurveySubmission, name).nullable is True

    fk_names = foreign_key_constraint_names(SurveySubmission)
    assert "fk_survey_submissions_survey_same_project" in fk_names
    assert "fk_survey_submissions_version_same_survey" in fk_names
    assert "fk_survey_submissions_store" in fk_names
    assert "fk_survey_submissions_store_same_project" in fk_names
    assert "fk_survey_submissions_public_link" in fk_names
    assert "fk_survey_submissions_public_link_same_survey" in fk_names
    assert "fk_survey_submissions_subject_same_project" in fk_names

    assert "uq_survey_submissions_external_submission_id" in index_names(SurveySubmission)
    assert get_relationship(SurveySubmission, "submitted_by").mapper.class_ is User


# -------------------------
# Response DB models
# -------------------------


def test_submission_table_shape():
    assert Submission.__tablename__ == "submissions"
    assert Submission.__bind_key__ == "response"

    assert get_column(Submission, "id").primary_key is True
    assert get_column(Submission, "core_submission_id").nullable is False
    assert get_column(Submission, "core_submission_id").unique is True
    assert get_column(Submission, "survey_id").nullable is False
    assert get_column(Submission, "survey_version_id").nullable is False
    assert get_column(Submission, "project_id").nullable is False
    assert get_column(Submission, "pseudonymous_subject_id").nullable is True
    assert get_column(Submission, "is_anonymous").nullable is False
    assert get_column(Submission, "submitted_at").nullable is False
    assert get_column(Submission, "metadata").nullable is True
    assert get_column(Submission, "created_at").nullable is False

    assert get_relationship(Submission, "answers").mapper.class_ is SubmissionAnswer
    assert get_relationship(Submission, "events").mapper.class_ is SubmissionEvent


def test_submission_answer_table_shape():
    assert SubmissionAnswer.__tablename__ == "submission_answers"
    assert SubmissionAnswer.__bind_key__ == "response"

    assert get_column(SubmissionAnswer, "id").primary_key is True
    assert get_column(SubmissionAnswer, "submission_id").nullable is False
    assert get_column(SubmissionAnswer, "question_key").nullable is False
    assert get_column(SubmissionAnswer, "answer_family").nullable is False
    assert get_column(SubmissionAnswer, "answer_value").nullable is False
    assert get_column(SubmissionAnswer, "created_at").nullable is False

    assert "uq_submission_answers_question" in unique_constraint_names(SubmissionAnswer)
    assert get_relationship(SubmissionAnswer, "submission").mapper.class_ is Submission


def test_submission_event_table_shape():
    assert SubmissionEvent.__tablename__ == "submission_events"
    assert SubmissionEvent.__bind_key__ == "response"

    assert get_column(SubmissionEvent, "id").primary_key is True
    assert get_column(SubmissionEvent, "submission_id").nullable is False
    assert get_column(SubmissionEvent, "event_type").nullable is False
    assert get_column(SubmissionEvent, "event_payload").nullable is True
    assert get_column(SubmissionEvent, "created_at").nullable is False

    assert get_relationship(SubmissionEvent, "submission").mapper.class_ is Submission


def test_survey_role_permissions_join_table_shape():
    table = survey_role_permissions

    assert table.name == "survey_role_permissions"
    assert set(table.c.keys()) == {"role_id", "permission_id"}
    assert table.c["role_id"].primary_key is True
    assert table.c["permission_id"].primary_key is True
