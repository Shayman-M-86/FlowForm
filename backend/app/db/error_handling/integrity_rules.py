"""Database integrity rules.

This layer translates Postgres constraint violations into ``AppError``
instances so the API can return a clean response instead of a generic 500.

It is *not* the primary validation layer. Most request validation lives in
Pydantic; cross-resource rules live in ``app/domain/``. Rules belong here
only when the invariant has already slipped past those upper layers —
either because no upstream layer can cover it, or because a code path
bypassed them. Concretely, rules cover three kinds of error:

1. **Race-prone uniqueness.** Service-level "does this slug exist?" checks
   cannot close the window between SELECT and INSERT under concurrency. The
   UNIQUE index closes it; the rule translates the resulting violation into
   a stable code (e.g. ``PROJECT_SLUG_CONFLICT``).

2. **Cross-table / state-machine invariants.** Constraints that span tables
   or transitions Pydantic cannot express — "a survey's default response
   store must belong to the same project," "cannot archive the actively
   published version while it is referenced." Enforced by FOREIGN KEYs and
   trigger functions; translated here so the client gets a meaningful code.

3. **Defence-in-depth for CHECK constraints that upper layers already
   cover.** When a Pydantic / domain rule encodes the same invariant as a
   CHECK, the CHECK still exists for direct ORM mutations, migrations, and
   future code. We deliberately do *not* register a rule for these in most
   cases — if the CHECK fires, the unmatched-rule path raises a 500, which
   is the correct signal that an API path bypassed validation.

Status codes used here
----------------------

Almost every rule returns **409 Conflict** — the request was structurally
valid but collided with current database state.

A small number of rules return **500 Internal Server Error** for CHECK
violations on *server-controlled* fields that clients cannot set
(submission ``status``, version ``status``/``compiled_schema``/
``published_at``). If those CHECKs fire, internal code wrote inconsistent
state — that is a server bug, not a client error, and the message says so
explicitly.

**No rule returns 422.** Structural invariants on client-supplied payloads
are validated upstream by Pydantic, where they belong. If you find yourself
reaching for 422 here, add the check to the request schema instead.

Other status codes (400, 404) are not used in this layer — those
conditions are cheaper to detect with a service-level read before opening
a transaction.

When NOT to add a rule here
---------------------------

Anything checkable at the request or service layer with a read or a
schema constraint should fail fast there. This file is reserved for
invariants that genuinely require the database to be the source of truth,
or for translating violations of upper-layer guards into specific
``AppError`` codes when there is real value in doing so.

How translation works
---------------------

``commit_with_err_handle`` / ``flush_with_err_handle`` catch
``DBAPIError``, look up the rule set for the supplied context object's
type, match on constraint name (preferred) or primary message text, build
an ``AppError`` with a stable ``code``, and re-raise. The normal API error
handler serialises it like any other ``AppError``.

If no rule matches, the original ``DBAPIError`` is logged and re-raised
as a 500. Reaching that path either means a new rule is needed *or* that
an upstream layer was bypassed — both worth investigating.
"""

from __future__ import annotations

from app.db.error_handling.error_translation import (
    DbErrorRule,
    check_rule,
    foreign_key_rule,
    message_rule,
    unique_rule,
)
from app.db.error_handling.errors import DbIntegrityError
from app.schema.orm.core import (
    Project,
    ProjectMembership,
    ProjectRole,
    ResponseSubjectMapping,
    Survey,
    SurveyLink,
    SurveyMembershipRole,
    SurveyQuestion,
    SurveyScoringRule,
    SurveySubmission,
    SurveyVersion,
)

type RuleContext = (
    Project
    | Survey
    | SurveyVersion
    | SurveyLink
    | ResponseSubjectMapping
    | SurveySubmission
    | SurveyQuestion
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
    "public_slug",
    "survey_link_id",
    "assigned_email",
    "requires_auth",
    "user_id",
    "submission_id",
    "survey_version_id",
    "has_submitted_by_user",
    "response_store_id",
    "external_submission_id",
    "pseudonymous_subject_id",
    "node_type",
    "survey_question_id",
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
        "public_slug": survey.public_slug,
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


def _survey_link_ctx(link: SurveyLink) -> dict[str, object]:
    return {
        "survey_link_id": link.id,
        "survey_id": link.survey_id,
        "name": link.name,
        "assigned_email": link.assigned_email,
        "requires_auth": link.requires_auth,
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
        "response_store_id": submission.response_store_id,
        "survey_link_id": submission.survey_link_id,
        "external_submission_id": submission.external_submission_id,
        "pseudonymous_subject_id": submission.pseudonymous_subject_id,
        "status": submission.status,
        "has_submitted_by_user": submission.submitted_by_user_id is not None,
    }


def _survey_question_ctx(question: SurveyQuestion) -> dict[str, object]:
    return {
        "survey_question_id": question.id,
        "survey_version_id": question.survey_version_id,
        "node_type": question.node_type,
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
        lambda ctx, _exc: DbIntegrityError(
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
        lambda ctx, _exc: DbIntegrityError(
            409,
            "SURVEY_SLUG_CONFLICT",
            f"Survey slug {ctx['public_slug']!r} is already in use.",
        ),
        extractor=_survey_ctx,
    ),
    foreign_key_rule(
        "fk_surveys_default_store",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "SURVEY_STORE_MISSING",
            f"Default response store id={ctx['default_response_store_id']} does not exist.",
        ),
        extractor=_survey_ctx,
    ),
    foreign_key_rule(
        "fk_surveys_default_store_same_project",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "SURVEY_STORE_PROJECT_CONFLICT",
            f"Default response store id={ctx['default_response_store_id']} does"
            f" not belong to project id={ctx['project_id']}.",
        ),
        extractor=_survey_ctx,
    ),
    foreign_key_rule(
        "fk_surveys_published_version_same_survey",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "SURVEY_PUBLISHED_VERSION_MISMATCH",
            f"Published version id={ctx['published_version_id']} does not belong to survey id={ctx['survey_id']}.",
        ),
        extractor=_survey_ctx,
    ),
    message_rule(
        "published_version_id must reference a published, non-deleted version of the same survey",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "SURVEY_PUBLISHED_VERSION_INVALID",
            f"Published version id={ctx['published_version_id']} must be a"
            f" published, non-deleted version of survey id={ctx['survey_id']}.",
        ),
        extractor=_survey_ctx,
    ),

)

SURVEY_VERSION_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "uq_survey_versions_survey_id_version_number",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "VERSION_NUMBER_CONFLICT",
            f"Survey already has version_number={ctx['version_number']}.",
        ),
        extractor=_survey_version_ctx,
    ),
    unique_rule(
        "uq_survey_versions_one_published",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "VERSION_PUBLISHED_CONFLICT",
            f"Survey id={ctx['survey_id']} already has a published version.",
        ),
        extractor=_survey_version_ctx,
    ),
    message_rule(
        "Cannot delete the active published survey version while it is referenced by surveys.published_version_id",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "VERSION_DELETE_PROTECTED",
            f"Published version id={ctx['survey_version_id']} cannot be deleted.",
        ),
        extractor=_survey_version_ctx,
    ),
    message_rule(
        "Cannot unpublish or soft delete the active published survey"
        " version while it is referenced by surveys.published_version_id",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "VERSION_STATE_PROTECTED",
            f"Published version id={ctx['survey_version_id']} cannot be unpublished or deleted.",
        ),
        extractor=_survey_version_ctx,
    ),
    # ck_survey_versions_published_requires_schema_and_timestamp
    #
    # This CHECK is internal-invariant defence in depth. The fields
    # (status, compiled_schema, published_at) are not exposed in any request
    # schema — surveys_repo.publish_version is the only code path that flips
    # status to "published" and it writes all three together. So there is no
    # Pydantic or service-level guard to add: nothing the client can send
    # could trigger this.
    #
    # If this CHECK ever fires, a non-API code path mutated SurveyVersion in
    # an inconsistent way — that is a server bug, not a client error.
    # The kept rule below intentionally returns 500 with a loud message so
    # the bug is visible in logs and to the caller, instead of disguising
    # the invariant violation as a 422.
    check_rule(
        "ck_survey_versions_published_requires_schema_and_timestamp",
        lambda ctx, _exc: DbIntegrityError(
            500,
            "VERSION_PUBLISH_STATE_INVALID",
            f"Server invariant violated: survey version id={ctx['survey_version_id']} reached"
            " status='published' without both compiled_schema and published_at."
            " This indicates a code path bypassed surveys_repo.publish_version.",
        ),
        extractor=_survey_version_ctx,
    ),
)

SURVEY_LINK_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "uq_survey_links_token_hash",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "LINK_TOKEN_CONFLICT",
            "This survey link token is already in use.",
        ),
        extractor=_survey_link_ctx,
    ),
    unique_rule(
        "uq_survey_links_survey_id_token_prefix",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "LINK_PREFIX_CONFLICT",
            f"Survey id={ctx['survey_id']} already has a link with this token prefix.",
        ),
        extractor=_survey_link_ctx,
    ),

)

RESPONSE_SUBJECT_MAPPING_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "uq_response_subject_mappings_project_id_user_id",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "SUBJECT_USER_CONFLICT",
            f"Project id={ctx['project_id']} already has a subject mapping for user id={ctx['user_id']}.",
        ),
        extractor=_subject_mapping_ctx,
    ),
    unique_rule(
        "uq_response_subject_mappings_project_id_pseudonymous_subject_id",
        lambda ctx, _exc: DbIntegrityError(
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
        lambda ctx, _exc: DbIntegrityError(
            409,
            "SUBMISSION_SURVEY_PROJECT_CONFLICT",
            f"Survey id={ctx['survey_id']} does not belong to project id={ctx['project_id']}.",
        ),
        extractor=_submission_ctx,
    ),
    foreign_key_rule(
        "fk_survey_submissions_version_same_survey",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "SUBMISSION_VERSION_SURVEY_CONFLICT",
            f"Survey version id={ctx['survey_version_id']} does not belong to survey id={ctx['survey_id']}.",
        ),
        extractor=_submission_ctx,
    ),
    foreign_key_rule(
        "fk_survey_submissions_store_same_project",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "SUBMISSION_STORE_PROJECT_CONFLICT",
            f"Response store id={ctx['response_store_id']} does not belong to project id={ctx['project_id']}.",
        ),
        extractor=_submission_ctx,
    ),
    foreign_key_rule(
        "fk_survey_submissions_survey_link_same_survey",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "SUBMISSION_LINK_SURVEY_CONFLICT",
            f"Survey link id={ctx['survey_link_id']} does not belong to survey id={ctx['survey_id']}.",
        ),
        extractor=_submission_ctx,
    ),
    foreign_key_rule(
        "fk_survey_submissions_subject_same_project",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "SUBMISSION_SUBJECT_PROJECT_CONFLICT",
            f"Pseudonymous subject id={ctx['pseudonymous_subject_id']!r} does not belong"
            f" to project id={ctx['project_id']}.",
        ),
        extractor=_submission_ctx,
    ),
    unique_rule(
        "uq_survey_submissions_external_submission_id",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "SUBMISSION_EXTERNAL_ID_CONFLICT",
            f"External submission id={ctx['external_submission_id']!r} is already in use "
            f"for response_store_id={ctx['response_store_id']}.",
        ),
        extractor=_submission_ctx,
    ),
    #
    # ck_survey_submissions_status_valid
    #
    # The `status` column is server-controlled — it is not exposed in any
    # request schema. Clients cannot set it. The default is "pending" and
    # internal delivery code transitions it to "stored" or "failed".
    # If this CHECK ever fires, internal code wrote an invalid status value.
    # That is a server bug, not a client error, so the rule returns 500 with
    # a loud message rather than disguising the violation as a 422.
    check_rule(
        "ck_survey_submissions_status_valid",
        lambda ctx, _exc: DbIntegrityError(
            500,
            "SUBMISSION_STATE_INVALID",
            f"Server invariant violated: submission id={ctx['submission_id']} was written with"
            f" invalid status={ctx['status']!r}."
            " Status is server-controlled and must be one of 'pending', 'stored', 'failed'.",
        ),
        extractor=_submission_ctx,
    ),
)

SURVEY_QUESTION_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "uq_survey_questions_survey_version_id_question_key",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "QUESTION_KEY_CONFLICT" if ctx.get("node_type") == "question" else "RULE_KEY_CONFLICT",
            f"Survey version id={ctx['survey_version_id']} already uses"
            f" {'question' if ctx.get('node_type') == 'question' else 'rule'}_key"
            f" (node id={ctx['survey_question_id']}).",
        ),
        extractor=_survey_question_ctx,
    ),
    unique_rule(
        "uq_survey_questions_survey_version_id_sort_key",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "SORT_KEY_CONFLICT",
            f"Survey version id={ctx['survey_version_id']} already uses that sort_key.",
        ),
        extractor=_survey_question_ctx,
    ),

    message_rule(
        "Cannot modify components of a published survey version",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "QUESTION_VERSION_LOCKED" if ctx.get("node_type") == "question" else "RULE_VERSION_LOCKED",
            f"Node id={ctx['survey_question_id']} cannot be changed because its survey version is published.",
        ),
        extractor=_survey_question_ctx,
    ),
)

SURVEY_SCORING_RULE_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "uq_survey_scoring_rules_survey_version_id_scoring_key",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "SCORING_KEY_CONFLICT",
            f"Survey version id={ctx['survey_version_id']} already uses scoring_key={ctx['scoring_key']!r}.",
        ),
        extractor=_survey_scoring_rule_ctx,
    ),
    message_rule(
        "Cannot modify components of a published survey version",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
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
        lambda ctx, _exc: DbIntegrityError(
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
        lambda ctx, _exc: DbIntegrityError(
            409,
            "PROJECT_MEMBERSHIP_CONFLICT",
            f"User id={ctx['user_id']} is already a member of project id={ctx['project_id']}.",
        ),
        extractor=_project_membership_ctx,
    ),
    foreign_key_rule(
        "fk_project_memberships_role_same_project",
        lambda ctx, _exc: DbIntegrityError(
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
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "SURVEY_MEMBERSHIP_SURVEY_MISMATCH",
            "The survey does not belong to the given project.",
        ),
        extractor=_survey_membership_role_ctx,
    ),
    foreign_key_rule(
        "fk_survey_membership_roles_membership_same_project",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "SURVEY_MEMBERSHIP_PROJECT_MISMATCH",
            "The membership does not belong to the given project.",
        ),
        extractor=_survey_membership_role_ctx,
    ),
    foreign_key_rule(
        "fk_survey_membership_roles_role_same_project",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
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
    SurveyLink: SURVEY_LINK_RULES,
    ResponseSubjectMapping: RESPONSE_SUBJECT_MAPPING_RULES,
    SurveySubmission: SURVEY_SUBMISSION_RULES,
    SurveyQuestion: SURVEY_QUESTION_RULES,
    SurveyScoringRule: SURVEY_SCORING_RULE_RULES,
    ProjectRole: PROJECT_ROLE_RULES,
    ProjectMembership: PROJECT_MEMBERSHIP_RULES,
    SurveyMembershipRole: SURVEY_MEMBERSHIP_ROLE_RULES,
}
