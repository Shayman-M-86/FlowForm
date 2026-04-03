from __future__ import annotations

import hashlib
import secrets

from app.schema.orm.core.audit_log import AuditLog
from app.schema.orm.core.project import Project, ProjectRole
from app.schema.orm.core.response_store import ResponseStore
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.survey_access import SurveyPublicLink, SurveyRole
from app.schema.orm.core.survey_content import SurveyQuestion, SurveyRule, SurveyScoringRule
from app.schema.orm.core.user import User


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


def make_survey_public_link(survey_id: int) -> SurveyPublicLink:
    _, prefix, token_hash = make_token_pair()
    link = SurveyPublicLink()
    link.survey_id = survey_id
    link.token_prefix = prefix
    link.token_hash = token_hash
    return link


def make_survey_role(project_id: int, name: str = "reviewer") -> SurveyRole:
    role = SurveyRole()
    role.project_id = project_id
    role.name = name
    return role


def make_audit_log(
    action: str = "created",
    entity_type: str = "survey",
    entity_id: int | None = None,
    user_id: int | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    log = AuditLog()
    log.action = action
    log.entity_type = entity_type
    log.entity_id = entity_id
    log.user_id = user_id
    if metadata is not None:
        log.log_metadata = metadata
    return log


def make_survey_rule(
    survey_version_id: int,
    rule_key: str = "r1",
    rule_schema: dict | None = None,
) -> SurveyRule:
    rule = SurveyRule()
    rule.survey_version_id = survey_version_id
    rule.rule_key = rule_key
    rule.rule_schema = rule_schema or {"condition": "always"}
    return rule


def make_survey_scoring_rule(
    survey_version_id: int,
    scoring_key: str = "s1",
    scoring_schema: dict | None = None,
) -> SurveyScoringRule:
    scoring_rule = SurveyScoringRule()
    scoring_rule.survey_version_id = survey_version_id
    scoring_rule.scoring_key = scoring_key
    scoring_rule.scoring_schema = scoring_schema or {"formula": "sum"}
    return scoring_rule


def make_survey_question(
    survey_version_id: int,
    question_key: str = "q1",
    question_schema: dict | None = None,
) -> SurveyQuestion:
    question = SurveyQuestion()
    question.survey_version_id = survey_version_id
    question.question_key = question_key
    question.question_schema = question_schema or {"type": "field", "label": "Question"}
    return question
