from __future__ import annotations

from app.db.error_handling.error_translation import (
    DbErrorRule,
    check_rule,
    foreign_key_rule,
    message_rule,
    unique_rule,
)
from app.domain.errors import AppError
from app.schema.orm.core import (
    Project,
    ProjectMembership,
    ProjectRole,
    ResponseSubjectMapping,
    Survey,
    SurveyMembershipRole,
    SurveyPublicLink,
    SurveyQuestion,
    SurveyRule,
    SurveyScoringRule,
    SurveySubmission,
    SurveyVersion,
)

type RuleContext = (
    Project
    | Survey
    | SurveyVersion
    | SurveyPublicLink
    | ResponseSubjectMapping
    | SurveySubmission
    | SurveyQuestion
    | SurveyRule
    | SurveyScoringRule
    | ProjectRole
    | ProjectMembership
    | SurveyMembershipRole
)
allowed_parameters = {
    "survey_id",
    "project_id",
    "slug",
    "visibility",
    "has_published_version",
    "version_number",
    "status",
    "is_published",
    "is_deleted",
    "public_link_id",
    "user_id",
    "submission_id",
    "survey_version_id",
    "has_submitted_by_user",
    "survey_question_id",
    "survey_rule_id",
    "survey_scoring_rule_id",
    "project_role_id",
    "name",
    "role_id",
    "default_response_store_id",
    "published_version_id",
}


def _project_ctx(project: Project) -> dict[str, object]:
    return {
        "project_id": project.id,
        "name": project.name,
        "slug": project.slug,
    }


def _survey_ctx(survey: Survey) -> dict[str, object]:
    return {
        "survey_id": survey.id,
        "project_id": survey.project_id,
        "visibility": survey.visibility,
        "has_published_version": survey.published_version_id is not None,
        "published_version_id": survey.published_version_id,
        "default_response_store_id": survey.default_response_store_id,
    }


def _survey_version_ctx(version: SurveyVersion) -> dict[str, object]:
    return {
        "survey_version_id": version.id,
        "survey_id": version.survey_id,
        "version_number": version.version_number,
        "status": version.status,
        "is_published": version.published_at is not None,
        "is_deleted": version.deleted_at is not None,
    }


def _public_link_ctx(link: SurveyPublicLink) -> dict[str, object]:
    return {
        "public_link_id": link.id,
        "survey_id": link.survey_id,
    }


def _subject_mapping_ctx(mapping: ResponseSubjectMapping) -> dict[str, object]:
    return {
        "project_id": mapping.project_id,
        "user_id": mapping.user_id,
    }


def _submission_ctx(submission: SurveySubmission) -> dict[str, object]:
    return {
        "submission_id": submission.id,
        "project_id": submission.project_id,
        "survey_id": submission.survey_id,
        "survey_version_id": submission.survey_version_id,
        "status": submission.status,
        "has_submitted_by_user": submission.submitted_by_user_id is not None,
    }


def _survey_question_ctx(question: SurveyQuestion) -> dict[str, object]:
    return {
        "survey_question_id": question.id,
        "survey_version_id": question.survey_version_id,
    }


def _survey_rule_ctx(rule: SurveyRule) -> dict[str, object]:
    return {
        "survey_rule_id": rule.id,
        "survey_version_id": rule.survey_version_id,
    }


def _survey_scoring_rule_ctx(rule: SurveyScoringRule) -> dict[str, object]:
    return {
        "survey_scoring_rule_id": rule.id,
        "survey_version_id": rule.survey_version_id,
    }


def _project_role_ctx(role: ProjectRole) -> dict[str, object]:
    return {
        "project_role_id": role.id,
        "project_id": role.project_id,
        "name": role.name,
    }


def _project_membership_ctx(membership: ProjectMembership) -> dict[str, object]:
    return {
        "project_id": membership.project_id,
        "user_id": membership.user_id,
        "role_id": membership.role_id,
    }


def _survey_membership_role_ctx(membership_role: SurveyMembershipRole) -> dict[str, object]:
    return {
        "survey_id": membership_role.survey_id,
        "role_id": membership_role.role_id,
    }


PROJECT_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "projects_slug_key",
        lambda ctx, _exc: AppError(
            409,
            "PROJECT_SLUG_CONFLICT",
            f"Project slug {ctx['slug']!r} is already in use.",
        ),
        extractor=_project_ctx,
    ),
)

SURVEY_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "surveys_public_slug_key",
        lambda ctx, _exc: AppError(
            409,
            "SURVEY_SLUG_CONFLICT",
            f"Survey slug {ctx['public_slug']!r} is already in use.",
        ),
        extractor=_survey_ctx,
    ),
    foreign_key_rule(
        "fk_surveys_default_store",
        lambda ctx, _exc: AppError(
            409,
            "SURVEY_STORE_MISSING",
            f"Default response store id={ctx['default_response_store_id']} does not exist.",
        ),
        extractor=_survey_ctx,
    ),
    foreign_key_rule(
        "fk_surveys_default_store_same_project",
        lambda ctx, _exc: AppError(
            409,
            "SURVEY_STORE_PROJECT_CONFLICT",
            f"Default response store id={ctx['default_response_store_id']} does"
            f" not belong to project id={ctx['project_id']}.",
        ),
        extractor=_survey_ctx,
    ),
    foreign_key_rule(
        "fk_surveys_published_version_same_survey",
        lambda ctx, _exc: AppError(
            409,
            "SURVEY_PUBLISHED_VERSION_MISMATCH",
            f"Published version id={ctx['published_version_id']} does not belong to survey id={ctx['survey_id']}.",
        ),
        extractor=_survey_ctx,
    ),
    message_rule(
        "published_version_id must reference a published, non-deleted version of the same survey",
        lambda ctx, _exc: AppError(
            409,
            "SURVEY_PUBLISHED_VERSION_INVALID",
            f"Published version id={ctx['published_version_id']} must be a"
            f" published, non-deleted version of survey id={ctx['survey_id']}.",
        ),
        extractor=_survey_ctx,
    ),
    check_rule(
        "ck_surveys_public_responses_requires_public_visibility",
        lambda ctx, _exc: AppError(  # noqa: ARG005
            422,
            "SURVEY_PUBLIC_VISIBILITY_INVALID",
            "A survey cannot allow public responses unless its visibility allows public access.",
        ),
        extractor=_survey_ctx,
    ),
    check_rule(
        "ck_surveys_public_requires_slug",
        lambda ctx, _exc: AppError(  # noqa: ARG005
            422,
            "SURVEY_SLUG_REQUIRED",
            "A public survey must have a public slug.",
        ),
        extractor=_survey_ctx,
    ),
)

SURVEY_VERSION_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "uq_survey_versions_survey_id_version_number",
        lambda ctx, _exc: AppError(
            409,
            "VERSION_NUMBER_CONFLICT",
            f"Survey already has version_number={ctx['version_number']}.",
        ),
        extractor=_survey_version_ctx,
    ),
    unique_rule(
        "uq_survey_versions_one_published",
        lambda ctx, _exc: AppError(
            409,
            "VERSION_PUBLISHED_CONFLICT",
            f"Survey id={ctx['survey_id']} already has a published version.",
        ),
        extractor=_survey_version_ctx,
    ),
    message_rule(
        "Cannot delete the active published survey version while it is referenced by surveys.published_version_id",
        lambda ctx, _exc: AppError(
            409,
            "VERSION_DELETE_PROTECTED",
            f"Published version id={ctx['survey_version_id']} cannot be deleted.",
        ),
        extractor=_survey_version_ctx,
    ),
    message_rule(
        "Cannot unpublish or soft delete the active published survey"
        " version while it is referenced by surveys.published_version_id",
        lambda ctx, _exc: AppError(
            409,
            "VERSION_STATE_PROTECTED",
            f"Published version id={ctx['survey_version_id']} cannot be unpublished or deleted.",
        ),
        extractor=_survey_version_ctx,
    ),
    check_rule(
        "ck_survey_versions_published_requires_schema_and_timestamp",
        lambda ctx, _exc: AppError(  # noqa: ARG005
            422,
            "VERSION_PUBLISH_STATE_INVALID",
            "A published version must have a compiled schema and published timestamp.",
        ),
        extractor=_survey_version_ctx,
    ),
)

SURVEY_PUBLIC_LINK_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "uq_survey_public_links_token_hash",
        lambda ctx, _exc: AppError(  # noqa: ARG005
            409,
            "LINK_TOKEN_CONFLICT",
            "This public link token is already in use.",
        ),
        extractor=_public_link_ctx,
    ),
    unique_rule(
        "uq_survey_public_links_survey_id_token_prefix",
        lambda ctx, _exc: AppError(
            409,
            "LINK_PREFIX_CONFLICT",
            f"Survey id={ctx['survey_id']} already has a link with this token prefix.",
        ),
        extractor=_public_link_ctx,
    ),
)

RESPONSE_SUBJECT_MAPPING_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "uq_response_subject_mappings_project_id_user_id",
        lambda ctx, _exc: AppError(
            409,
            "SUBJECT_USER_CONFLICT",
            f"Project id={ctx['project_id']} already has a subject mapping for user id={ctx['user_id']}.",
        ),
        extractor=_subject_mapping_ctx,
    ),
    unique_rule(
        "uq_response_subject_mappings_project_id_pseudonymous_subject_id",
        lambda ctx, _exc: AppError(
            409,
            "SUBJECT_ID_CONFLICT",
            f"Project id={ctx['project_id']} already uses pseudonymous subject id={ctx['pseudonymous_subject_id']}.",
        ),
        extractor=_subject_mapping_ctx,
    ),
)

SURVEY_SUBMISSION_RULES: tuple[DbErrorRule, ...] = (
    foreign_key_rule(
        "fk_survey_submissions_survey_same_project",
        lambda ctx, _exc: AppError(
            409,
            "SUBMISSION_SURVEY_PROJECT_CONFLICT",
            f"Survey id={ctx['survey_id']} does not belong to project id={ctx['project_id']}.",
        ),
        extractor=_submission_ctx,
    ),
    foreign_key_rule(
        "fk_survey_submissions_version_same_survey",
        lambda ctx, _exc: AppError(
            409,
            "SUBMISSION_VERSION_SURVEY_CONFLICT",
            f"Survey version id={ctx['survey_version_id']} does not belong to survey id={ctx['survey_id']}.",
        ),
        extractor=_submission_ctx,
    ),
    foreign_key_rule(
        "fk_survey_submissions_store_same_project",
        lambda ctx, _exc: AppError(
            409,
            "SUBMISSION_STORE_PROJECT_CONFLICT",
            f"Response store id={ctx['response_store_id']} does not belong to project id={ctx['project_id']}.",
        ),
        extractor=_submission_ctx,
    ),
    foreign_key_rule(
        "fk_survey_submissions_public_link_same_survey",
        lambda ctx, _exc: AppError(
            409,
            "SUBMISSION_LINK_SURVEY_CONFLICT",
            f"Public link id={ctx['public_link_id']} does not belong to survey id={ctx['survey_id']}.",
        ),
        extractor=_submission_ctx,
    ),
    foreign_key_rule(
        "fk_survey_submissions_subject_same_project",
        lambda ctx, _exc: AppError(
            409,
            "SUBMISSION_SUBJECT_PROJECT_CONFLICT",
            f"Pseudonymous subject id={ctx['pseudonymous_subject_id']!r} does not belong"
            f" to project id={ctx['project_id']}.",
        ),
        extractor=_submission_ctx,
    ),
    unique_rule(
        "uq_survey_submissions_external_submission_id",
        lambda ctx, _exc: AppError(
            409,
            "SUBMISSION_EXTERNAL_ID_CONFLICT",
            f"External submission id={ctx['external_submission_id']!r} is already in use "
            f"for response_store_id={ctx['response_store_id']}.",
        ),
        extractor=_submission_ctx,
    ),
    check_rule(
        "ck_survey_submissions_submitted_at_after_started_at",
        lambda ctx, _exc: AppError(  # noqa: ARG005
            422,
            "SUBMISSION_TIME_ORDER_INVALID",
            "Submission submitted_at cannot be earlier than started_at.",
        ),
        extractor=_submission_ctx,
    ),
    check_rule(
        "ck_survey_submissions_status_valid",
        lambda ctx, _exc: AppError(
            422,
            "SUBMISSION_STATE_INVALID",
            f"Submission has invalid status={ctx['status']!r}.",
        ),
        extractor=_submission_ctx,
    ),
)

SURVEY_QUESTION_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "uq_survey_questions_survey_version_id_question_key",
        lambda ctx, _exc: AppError(
            409,
            "QUESTION_KEY_CONFLICT",
            f"Survey version id={ctx['survey_version_id']} already uses question_key={ctx['question_key']!r}.",
        ),
        extractor=_survey_question_ctx,
    ),
    message_rule(
        "Cannot modify components of a published survey version",
        lambda ctx, _exc: AppError(
            409,
            "QUESTION_VERSION_LOCKED",
            f"Question id={ctx['survey_question_id']} cannot be changed because its survey version is published.",
        ),
        extractor=_survey_question_ctx,
    ),
)
SURVEY_RULE_CONTENT_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "uq_survey_rules_survey_version_id_rule_key",
        lambda ctx, _exc: AppError(
            409,
            "RULE_KEY_CONFLICT",
            f"Survey version id={ctx['survey_version_id']} already uses rule_key={ctx['rule_key']!r}.",
        ),
        extractor=_survey_rule_ctx,
    ),
    message_rule(
        "Cannot modify components of a published survey version",
        lambda ctx, _exc: AppError(  # noqa: ARG005
            409,
            "RULE_VERSION_LOCKED",
            "Rules cannot be changed on a published survey version.",
        ),
        extractor=_survey_rule_ctx,
    ),
)

SURVEY_SCORING_RULE_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "uq_survey_scoring_rules_survey_version_id_scoring_key",
        lambda ctx, _exc: AppError(
            409,
            "SCORING_KEY_CONFLICT",
            f"Survey version id={ctx['survey_version_id']} already uses scoring_key={ctx['scoring_key']!r}.",
        ),
        extractor=_survey_scoring_rule_ctx,
    ),
    message_rule(
        "Cannot modify components of a published survey version",
        lambda ctx, _exc: AppError(  # noqa: ARG005
            409,
            "SCORING_VERSION_LOCKED",
            "Scoring rules cannot be changed on a published survey version.",
        ),
        extractor=_survey_scoring_rule_ctx,
    ),
)
PROJECT_ROLE_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "uq_project_roles_project_name",
        lambda ctx, _exc: AppError(
            409,
            "PROJECT_ROLE_NAME_CONFLICT",
            f"Project already has a role named {ctx['name']!r}.",
        ),
        extractor=_project_role_ctx,
    ),
)
PROJECT_MEMBERSHIP_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "uq_project_memberships_user_project",
        lambda ctx, _exc: AppError(
            409,
            "PROJECT_MEMBERSHIP_CONFLICT",
            f"User id={ctx['user_id']} is already a member of project id={ctx['project_id']}.",
        ),
        extractor=_project_membership_ctx,
    ),
    foreign_key_rule(
        "fk_project_memberships_role_same_project",
        lambda ctx, _exc: AppError(
            409,
            "PROJECT_ROLE_MISMATCH",
            f"Role id={ctx['role_id']} does not belong to project id={ctx['project_id']}.",
        ),
        extractor=_project_membership_ctx,
    ),
)
SURVEY_MEMBERSHIP_ROLE_RULES: tuple[DbErrorRule, ...] = (
    foreign_key_rule(
        "fk_survey_membership_roles_survey_same_project",
        lambda ctx, _exc: AppError(  # noqa: ARG005
            409,
            "SURVEY_MEMBERSHIP_SURVEY_MISMATCH",
            "The survey does not belong to the given project.",
        ),
        extractor=_survey_membership_role_ctx,
    ),
    foreign_key_rule(
        "fk_survey_membership_roles_membership_same_project",
        lambda ctx, _exc: AppError(  # noqa: ARG005
            409,
            "SURVEY_MEMBERSHIP_PROJECT_MISMATCH",
            "The membership does not belong to the given project.",
        ),
        extractor=_survey_membership_role_ctx,
    ),
    foreign_key_rule(
        "fk_survey_membership_roles_role_same_project",
        lambda ctx, _exc: AppError(  # noqa: ARG005
            409,
            "SURVEY_ROLE_PROJECT_MISMATCH",
            "The survey role does not belong to the given project.",
        ),
        extractor=_survey_membership_role_ctx,
    ),
)

RULES_BY_CONTEXT: dict[type[object], tuple[DbErrorRule, ...]] = {
    Project: PROJECT_RULES,
    Survey: SURVEY_RULES,
    SurveyVersion: SURVEY_VERSION_RULES,
    SurveyPublicLink: SURVEY_PUBLIC_LINK_RULES,
    ResponseSubjectMapping: RESPONSE_SUBJECT_MAPPING_RULES,
    SurveySubmission: SURVEY_SUBMISSION_RULES,
    SurveyQuestion: SURVEY_QUESTION_RULES,
    SurveyRule: SURVEY_RULE_CONTENT_RULES,
    SurveyScoringRule: SURVEY_SCORING_RULE_RULES,
    ProjectRole: PROJECT_ROLE_RULES,
    ProjectMembership: PROJECT_MEMBERSHIP_RULES,
    SurveyMembershipRole: SURVEY_MEMBERSHIP_ROLE_RULES,
}
