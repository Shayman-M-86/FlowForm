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
    ProjectInvitation,
    ProjectMembership,
    ProjectParticipant,
    ProjectRole,
    ProjectSubject,
    ProjectSubjectIdentity,
    ProjectSubjectToken,
    SubjectIpObservation,
    SubmissionAnswerSlot,
    SubmissionEvent,
    SubmissionSession,
    Survey,
    SurveyEncryptionKey,
    SurveyLink,
    SurveyMembershipRole,
    SurveyQuestion,
    SurveyRole,
    SurveyScoringRule,
    SurveyVersion,
    User,
)
from app.schema.orm.response import ResponseAnswer, ResponseEnvelope

type RuleContext = (
    User
    | Project
    | ProjectInvitation
    | Survey
    | SurveyVersion
    | SurveyLink
    | ProjectParticipant
    | ProjectSubject
    | ProjectSubjectIdentity
    | ProjectSubjectToken
    | SubjectIpObservation
    | SubmissionSession
    | SubmissionAnswerSlot
    | SubmissionEvent
    | SurveyQuestion
    | SurveyEncryptionKey
    | SurveyRole
    | SurveyScoringRule
    | ProjectRole
    | ProjectMembership
    | SurveyMembershipRole
    | ResponseEnvelope
    | ResponseAnswer
)
# Fields that may be surfaced to API clients (in error messages) *and* written
# to server logs. This set is deliberately restricted to values the user
# supplied or chose (emails, slugs, names, keys, version numbers) plus
# server-controlled enum/bool descriptors that carry no internal identifier.
#
# Internal surrogate identifiers — auto-assigned integer primary keys and the
# foreign keys referencing them (``*_id``), and the pseudonymous correlation
# UUID — are intentionally excluded. They must never leak to clients, and per
# project policy they are kept out of the log summaries too. ``summarize_context``
# in ``error_registry.py`` iterates this set, so dropping a name here removes it
# from both the unmatched-fallback response body and the logger extras.
allowed_parameters = {
    "auth0_user_id",
    "email",
    "slug",
    "visibility",
    "has_published_version",
    "version_number",
    "status",
    "is_published",
    "is_deleted",
    "public_slug",
    "link_type",
    "assignment_source",
    "session_status",
    "event_type",
    "subject_code",
    "normalized_email",
    "node_type",
    "scoring_key",
    "name",
    "invited_email",
    "client_mutation_id",
    "kms_context_version",
}


def _user_ctx(user: User) -> dict[str, object]:
    return {
        "auth0_user_id": user.auth0_user_id,
        "email": user.email,
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
        "project_id": link.project_id,
        "survey_id": link.survey_id,
        "name": link.name,
        "link_type": link.link_type,
        "assignment_source": link.assignment_source,
        "assigned_participant_id": link.assigned_participant_id,
    }


def _project_subject_ctx(subject: ProjectSubject) -> dict[str, object]:
    return {
        "project_id": subject.project_id,
        "subject_code": subject.subject_code,
    }


def _project_subject_identity_ctx(identity: ProjectSubjectIdentity) -> dict[str, object]:
    return {
        "identity_id": identity.id,
        "project_id": identity.project_id,
        "project_subject_id": identity.project_subject_id,
        "user_id": identity.user_id,
        "normalized_email": identity.normalized_email,
    }


def _project_participant_ctx(participant: ProjectParticipant) -> dict[str, object]:
    return {
        "participant_id": participant.id,
        "project_id": participant.project_id,
        "project_subject_id": participant.project_subject_id,
        "identity_id": participant.identity_id,
    }


def _project_subject_token_ctx(token: ProjectSubjectToken) -> dict[str, object]:
    return {
        "token_id": token.id,
        "project_id": token.project_id,
        "project_subject_id": token.project_subject_id,
    }


def _subject_ip_observation_ctx(observation: SubjectIpObservation) -> dict[str, object]:
    return {
        "ip_observation_id": observation.id,
        "project_id": observation.project_id,
        "project_subject_id": observation.project_subject_id,
        "submission_session_id": observation.submission_session_id,
    }


def _submission_session_ctx(session: SubmissionSession) -> dict[str, object]:
    return {
        "session_id": session.id,
        "project_id": session.project_id,
        "survey_id": session.survey_id,
        "survey_version_id": session.survey_version_id,
        "response_store_id": session.response_store_id,
        "survey_link_id": session.link_id,
        "project_subject_id": session.project_subject_id,
        "session_status": session.session_status,
    }


def _submission_event_ctx(event: SubmissionEvent) -> dict[str, object]:
    return {
        "event_id": event.id,
        "session_id": event.session_id,
        "survey_version_id": event.survey_version_id,
        "event_type": event.event_type,
        "question_node_id": event.question_node_id,
    }


def _survey_question_ctx(question: SurveyQuestion) -> dict[str, object]:
    return {
        "survey_question_id": question.id,
        "survey_version_id": question.survey_version_id,
        "node_type": question.node_type,
    }


def _survey_encryption_key_ctx(key: SurveyEncryptionKey) -> dict[str, object]:
    return {
        "survey_encryption_key_id": key.id,
        "project_id": key.project_id,
        "survey_id": key.survey_id,
        "kms_context_version": key.kms_context_version,
    }


def _survey_scoring_rule_ctx(rule: SurveyScoringRule) -> dict[str, object]:
    return {
        "survey_scoring_rule_id": rule.id,
        "survey_version_id": rule.survey_version_id,
        "scoring_key": rule.scoring_key,
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
        "status": membership.status,
    }


def _survey_membership_role_ctx(membership_role: SurveyMembershipRole) -> dict[str, object]:
    return {
        "survey_id": membership_role.survey_id,
        "role_id": membership_role.role_id,
    }


def _response_envelope_ctx(envelope: ResponseEnvelope) -> dict[str, object]:
    return {
        "envelope_id": envelope.id,
    }


def _submission_answer_slot_ctx(slot: SubmissionAnswerSlot) -> dict[str, object]:
    return {
        "answer_slot_id": slot.id,
        "session_id": slot.submission_session_id,
        "survey_version_id": slot.survey_version_id,
        "question_node_id": slot.question_node_id,
    }


def _response_answer_ctx(answer: ResponseAnswer) -> dict[str, object]:
    return {
        "envelope_id": answer.envelope_id,
    }



def _invitation_ctx(invitation: ProjectInvitation) -> dict[str, object]:
    return {
        "invitation_id": invitation.id,
        "project_id": invitation.project_id,
        "invited_email": invitation.invited_email,
        "role_id": invitation.role_id,
        "status": invitation.status,
    }


USER_RULES: tuple[DbErrorRule, ...] = (
    # No users_email_key rule: email is intentionally not unique (one email may
    # back several Auth0 identities). auth0_user_id is the uniqueness guarantor.
    unique_rule(
        "users_auth0_user_id_key",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "AUTH0_ID_CONFLICT",
            f"Auth0 user id {ctx['auth0_user_id']!r} is already associated with another account.",
        ),
        extractor=_user_ctx,
    ),
)

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
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "SURVEY_STORE_MISSING",
            "The default response store does not exist.",
        ),
        extractor=_survey_ctx,
    ),
    foreign_key_rule(
        "fk_surveys_default_store_same_project",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "SURVEY_STORE_PROJECT_CONFLICT",
            "The default response store does not belong to this project.",
        ),
        extractor=_survey_ctx,
    ),
    foreign_key_rule(
        "fk_surveys_published_version_same_survey",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "SURVEY_PUBLISHED_VERSION_MISMATCH",
            "The published version does not belong to this survey.",
        ),
        extractor=_survey_ctx,
    ),
    message_rule(
        "published_version_id must reference a published, non-deleted version of the same survey",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "SURVEY_PUBLISHED_VERSION_INVALID",
            "The published version must be a published, non-deleted version of this survey.",
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
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "VERSION_PUBLISHED_CONFLICT",
            "This survey already has a published version.",
        ),
        extractor=_survey_version_ctx,
    ),
    message_rule(
        "Cannot delete the active published survey version while it is referenced by surveys.published_version_id",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "VERSION_DELETE_PROTECTED",
            "The active published survey version cannot be deleted.",
        ),
        extractor=_survey_version_ctx,
    ),
    message_rule(
        "Cannot unpublish or soft delete the active published survey"
        " version while it is referenced by surveys.published_version_id",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "VERSION_STATE_PROTECTED",
            "The active published survey version cannot be unpublished or deleted.",
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
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            500,
            "VERSION_PUBLISH_STATE_INVALID",
            "Server invariant violated: a survey version reached"
            " status='published' without both compiled_schema and published_at."
            " This indicates a code path bypassed surveys_repo.publish_version.",
        ),
        extractor=_survey_version_ctx,
    ),
)

SURVEY_LINK_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "uq_survey_links_token",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "LINK_TOKEN_CONFLICT",
            "This survey link token is already in use.",
        ),
        extractor=_survey_link_ctx,
    ),
    foreign_key_rule(
        "fk_survey_links_survey_same_project",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "LINK_SURVEY_PROJECT_CONFLICT",
            "The survey does not belong to this project.",
        ),
        extractor=_survey_link_ctx,
    ),
    foreign_key_rule(
        "fk_survey_links_assigned_participant_same_project",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "LINK_PARTICIPANT_PROJECT_CONFLICT",
            "The assigned participant does not belong to this project.",
        ),
        extractor=_survey_link_ctx,
    ),
)

PROJECT_SUBJECT_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "uq_project_subjects_project_id_subject_code",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "SUBJECT_CODE_CONFLICT",
            f"This project already uses subject code={ctx['subject_code']!r}.",
        ),
        extractor=_project_subject_ctx,
    ),
)

PROJECT_SUBJECT_IDENTITY_RULES: tuple[DbErrorRule, ...] = (
    foreign_key_rule(
        "fk_project_subject_identities_subject_same_project",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "IDENTITY_SUBJECT_PROJECT_CONFLICT",
            "The project subject does not belong to this project.",
        ),
        extractor=_project_subject_identity_ctx,
    ),
    unique_rule(
        "uq_project_subject_identities_active_user",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "IDENTITY_USER_CONFLICT",
            "This user already has an active subject in this project.",
        ),
        extractor=_project_subject_identity_ctx,
    ),
    unique_rule(
        "uq_project_subject_identities_subject_active_email",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "IDENTITY_SUBJECT_EMAIL_CONFLICT",
            f"This subject already has an active identity for email={ctx['normalized_email']!r}.",
        ),
        extractor=_project_subject_identity_ctx,
    ),
    unique_rule(
        "uq_project_subject_identities_project_verified_email",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "IDENTITY_VERIFIED_EMAIL_CONFLICT",
            f"Email={ctx['normalized_email']!r} is already verified for another subject in this project.",
        ),
        extractor=_project_subject_identity_ctx,
    ),
)

PROJECT_PARTICIPANT_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "uq_project_participants_project_subject",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "PARTICIPANT_SUBJECT_CONFLICT",
            "This subject is already a participant in this project.",
        ),
        extractor=_project_participant_ctx,
    ),
    foreign_key_rule(
        "fk_project_participants_subject_same_project",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "PARTICIPANT_SUBJECT_PROJECT_CONFLICT",
            "The project subject does not belong to this project.",
        ),
        extractor=_project_participant_ctx,
    ),
    foreign_key_rule(
        "fk_project_participants_identity_same_subject",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "PARTICIPANT_IDENTITY_SUBJECT_CONFLICT",
            "The identity does not belong to this subject.",
        ),
        extractor=_project_participant_ctx,
    ),
    foreign_key_rule(
        "fk_survey_links_assigned_participant_same_project",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "PARTICIPANT_IN_USE",
            "This participant is assigned to one or more survey links and cannot be deleted.",
        ),
        extractor=_project_participant_ctx,
    ),
)

PROJECT_SUBJECT_TOKEN_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "uq_project_subject_tokens_token_hash",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "SUBJECT_TOKEN_CONFLICT",
            "This subject recognition token is already in use.",
        ),
        extractor=_project_subject_token_ctx,
    ),
    foreign_key_rule(
        "fk_project_subject_tokens_subject_same_project",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "SUBJECT_TOKEN_PROJECT_CONFLICT",
            "The project subject does not belong to this project.",
        ),
        extractor=_project_subject_token_ctx,
    ),
)

SUBJECT_IP_OBSERVATION_RULES: tuple[DbErrorRule, ...] = (
    foreign_key_rule(
        "fk_subject_ip_observations_subject_same_project",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "IP_OBSERVATION_SUBJECT_PROJECT_CONFLICT",
            "The project subject does not belong to this project.",
        ),
        extractor=_subject_ip_observation_ctx,
    ),
    foreign_key_rule(
        "fk_subject_ip_observations_session_same_project",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "IP_OBSERVATION_SESSION_PROJECT_CONFLICT",
            "The submission session does not belong to this project.",
        ),
        extractor=_subject_ip_observation_ctx,
    ),
    foreign_key_rule(
        "fk_subject_ip_observations_session_subject_match",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "IP_OBSERVATION_SESSION_SUBJECT_MISMATCH",
            "The subject does not match the subject attached to this submission session.",
        ),
        extractor=_subject_ip_observation_ctx,
    ),
)

SUBMISSION_SESSION_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "uq_submission_sessions_browser_session_token_hash",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "SESSION_TOKEN_CONFLICT",
            "This browser session token is already in use.",
        ),
        extractor=_submission_session_ctx,
    ),
    foreign_key_rule(
        "fk_submission_sessions_survey_same_project",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "SESSION_SURVEY_PROJECT_CONFLICT",
            "The survey does not belong to this project.",
        ),
        extractor=_submission_session_ctx,
    ),
    foreign_key_rule(
        "fk_submission_sessions_version_same_survey",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "SESSION_VERSION_SURVEY_CONFLICT",
            "The survey version does not belong to this survey.",
        ),
        extractor=_submission_session_ctx,
    ),
    foreign_key_rule(
        "fk_submission_sessions_store_same_project",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "SESSION_STORE_PROJECT_CONFLICT",
            "The response store does not belong to this project.",
        ),
        extractor=_submission_session_ctx,
    ),
    foreign_key_rule(
        "fk_submission_sessions_link_same_survey",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "SESSION_LINK_SURVEY_CONFLICT",
            "The survey link does not belong to this survey.",
        ),
        extractor=_submission_session_ctx,
    ),
    foreign_key_rule(
        "fk_submission_sessions_project_subject_same_project",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "SESSION_SUBJECT_PROJECT_CONFLICT",
            "The project subject does not belong to this project.",
        ),
        extractor=_submission_session_ctx,
    ),
    #
    # ck_submission_sessions_session_status_valid
    #
    # `session_status` is server-controlled — it is not exposed in any
    # request schema. The default is "in_progress" and internal code
    # transitions it to "completed" or "abandoned". If this CHECK ever
    # fires, internal code wrote an invalid status value — a server bug,
    # not a client error.
    check_rule(
        "ck_submission_sessions_session_status_valid",
        lambda ctx, _exc: DbIntegrityError(
            500,
            "SESSION_STATE_INVALID",
            "Server invariant violated: a submission session was written with"
            f" invalid session_status={ctx['session_status']!r}."
            " session_status is server-controlled and must be one of"
            " 'in_progress', 'completed', 'abandoned'.",
        ),
        extractor=_submission_session_ctx,
    ),
    #
    # ck_submission_sessions_completed_at_consistent
    #
    # `completed_at` is server-controlled, written only when a session
    # transitions to "completed". The CHECK requires completed_at to be set
    # iff the session is completed. If it fires, internal code wrote an
    # inconsistent state — a server bug, not a client error.
    check_rule(
        "ck_submission_sessions_completed_at_consistent",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            500,
            "SESSION_COMPLETION_STATE_INVALID",
            "Server invariant violated: a submission session has an inconsistent"
            " completed_at for its session_status.",
        ),
        extractor=_submission_session_ctx,
    ),
)

SUBMISSION_EVENT_RULES: tuple[DbErrorRule, ...] = (
    foreign_key_rule(
        "fk_submission_events_session_version",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "EVENT_SESSION_VERSION_CONFLICT",
            "The session does not belong to this survey version.",
        ),
        extractor=_submission_event_ctx,
    ),
    foreign_key_rule(
        "fk_submission_events_question_node_same_version",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "EVENT_QUESTION_VERSION_CONFLICT",
            "The question node does not belong to this survey version.",
        ),
        extractor=_submission_event_ctx,
    ),
    #
    # ck_submission_events_event_type_valid
    #
    # `event_type` is server-controlled — it is not exposed in any request
    # schema. If this CHECK fires, internal code wrote an invalid event
    # type — a server bug, not a client error.
    check_rule(
        "ck_submission_events_event_type_valid",
        lambda ctx, _exc: DbIntegrityError(
            500,
            "EVENT_TYPE_INVALID",
            "Server invariant violated: a submission event was written with"
            f" invalid event_type={ctx['event_type']!r}.",
        ),
        extractor=_submission_event_ctx,
    ),
)

SURVEY_QUESTION_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "survey_questions_pkey",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "NODE_ID_CONFLICT",
            "A node with this ID already exists.",
        ),
        extractor=_survey_question_ctx,
    ),
    unique_rule(
        "uq_survey_questions_survey_version_id_question_key",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "QUESTION_KEY_CONFLICT" if ctx.get("node_type") == "question" else "RULE_KEY_CONFLICT",
            f"This survey version already uses that"
            f" {'question' if ctx.get('node_type') == 'question' else 'rule'}_key.",
        ),
        extractor=_survey_question_ctx,
    ),
    unique_rule(
        "uq_survey_questions_survey_version_id_sort_key",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "SORT_KEY_CONFLICT",
            "This survey version already uses that sort_key.",
        ),
        extractor=_survey_question_ctx,
    ),

    message_rule(
        "Cannot modify components of a published survey version",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "QUESTION_VERSION_LOCKED" if ctx.get("node_type") == "question" else "RULE_VERSION_LOCKED",
            "This node cannot be changed because its survey version is published.",
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
            f"This survey version already uses scoring_key={ctx['scoring_key']!r}.",
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


def _survey_role_ctx(role: SurveyRole) -> dict[str, object]:
    return {
        "project_id": role.project_id,
        "name": role.name,
    }


SURVEY_ROLE_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "uq_survey_roles_project_id_name",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "SURVEY_ROLE_NAME_CONFLICT",
            f"Project already has a survey role named {ctx['name']!r}.",
        ),
        extractor=_survey_role_ctx,
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
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "PROJECT_MEMBERSHIP_CONFLICT",
            "This user is already a member of this project.",
        ),
        extractor=_project_membership_ctx,
    ),
    foreign_key_rule(
        "fk_project_memberships_role_same_project",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "PROJECT_ROLE_MISMATCH",
            "The role does not belong to this project.",
        ),
        extractor=_project_membership_ctx,
    ),
    # ck_project_memberships_status_valid
    #
    # status is server-controlled — clients cannot set it. If this CHECK fires,
    # internal code wrote an invalid value. Return 500 so the bug is surfaced.
    check_rule(
        "ck_project_memberships_status_valid",
        lambda ctx, _exc: DbIntegrityError(
            500,
            "MEMBERSHIP_STATE_INVALID",
            "Server invariant violated: a project membership was"
            f" written with invalid status={ctx['status']!r}.",
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

PROJECT_INVITATION_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "uq_project_invitations_token_hash",
        lambda ctx, _exc: DbIntegrityError(
            500,
            "INVITATION_TOKEN_COLLISION",
            "Invitation token collision — retry the request.",
        ),
        extractor=_invitation_ctx,
    ),
    unique_rule(
        "uq_project_invitations_pending_project_email",
        lambda ctx, _exc: DbIntegrityError(
            409,
            "INVITATION_EXISTS",
            f"A pending invitation already exists for {ctx['invited_email']!r} in this project.",
        ),
        extractor=_invitation_ctx,
    ),
    foreign_key_rule(
        "fk_project_invitations_role_same_project",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "INVITATION_ROLE_MISMATCH",
            "The role does not belong to this project.",
        ),
        extractor=_invitation_ctx,
    ),
    # ck_project_invitations_status_valid
    #
    # status is server-controlled — only MembersService writes it. If this CHECK
    # fires, a code path wrote an invalid status value. Return 500 so the bug
    # is visible rather than disguised as a client error.
    check_rule(
        "ck_project_invitations_status_valid",
        lambda ctx, _exc: DbIntegrityError(
            500,
            "INVITATION_STATE_INVALID",
            "Server invariant violated: a project invitation was written"
            f" with invalid status={ctx['status']!r}.",
        ),
        extractor=_invitation_ctx,
    ),
)

SURVEY_ENCRYPTION_KEY_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "uq_survey_encryption_keys_survey",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "SURVEY_ENCRYPTION_KEY_EXISTS",
            "A survey encryption key already exists for this survey.",
        ),
        extractor=_survey_encryption_key_ctx,
    ),
    unique_rule(
        "uq_survey_encryption_keys_project_survey",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "SURVEY_ENCRYPTION_KEY_EXISTS",
            "A survey encryption key already exists for this survey.",
        ),
        extractor=_survey_encryption_key_ctx,
    ),
    foreign_key_rule(
        "fk_survey_encryption_keys_survey_same_project",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "SURVEY_ENCRYPTION_KEY_SURVEY_MISMATCH",
            "The survey encryption key does not reference a survey in this project.",
        ),
        extractor=_survey_encryption_key_ctx,
    ),
    check_rule(
        "ck_survey_encryption_keys_wrapped_key_len",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            500,
            "SURVEY_ENCRYPTION_KEY_INVALID",
            "Server invariant violated: a survey encryption key was written without wrapped key material.",
        ),
        extractor=_survey_encryption_key_ctx,
    ),
    check_rule(
        "ck_survey_encryption_keys_kms_key_arn_len",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            500,
            "SURVEY_ENCRYPTION_KEY_INVALID",
            "Server invariant violated: a survey encryption key was written without valid KMS key metadata.",
        ),
        extractor=_survey_encryption_key_ctx,
    ),
    check_rule(
        "ck_survey_encryption_keys_kms_context_version_valid",
        lambda ctx, _exc: DbIntegrityError(
            500,
            "SURVEY_ENCRYPTION_KEY_INVALID",
            "Server invariant violated: a survey encryption key was written"
            f" with invalid kms_context_version={ctx['kms_context_version']!r}.",
        ),
        extractor=_survey_encryption_key_ctx,
    ),
)

RESPONSE_ENVELOPE_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "uq_response_envelopes_session_locator",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "ENVELOPE_EXISTS",
            "A response envelope already exists for this session.",
        ),
        extractor=_response_envelope_ctx,
    ),
)

SUBMISSION_ANSWER_SLOT_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "uq_submission_answer_slots_session_question",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "ANSWER_SLOT_EXISTS",
            "An answer slot already exists for this session and question.",
        ),
        extractor=_submission_answer_slot_ctx,
    ),
)

RESPONSE_ANSWER_RULES: tuple[DbErrorRule, ...] = (
    unique_rule(
        "uq_response_answers_envelope_id_nonce",
        lambda ctx, _exc: DbIntegrityError(  # noqa: ARG005
            409,
            "ANSWER_NONCE_CONFLICT",
            "An answer with this nonce already exists in this envelope.",
        ),
        extractor=_response_answer_ctx,
    ),
)

RULES_BY_CONTEXT: dict[type[object], tuple[DbErrorRule, ...]] = {
    User: USER_RULES,
    Project: PROJECT_RULES,
    ProjectInvitation: PROJECT_INVITATION_RULES,
    Survey: SURVEY_RULES,
    SurveyVersion: SURVEY_VERSION_RULES,
    SurveyLink: SURVEY_LINK_RULES,
    SurveyRole: SURVEY_ROLE_RULES,
    ProjectParticipant: PROJECT_PARTICIPANT_RULES,
    ProjectSubject: PROJECT_SUBJECT_RULES,
    ProjectSubjectIdentity: PROJECT_SUBJECT_IDENTITY_RULES,
    ProjectSubjectToken: PROJECT_SUBJECT_TOKEN_RULES,
    SubjectIpObservation: SUBJECT_IP_OBSERVATION_RULES,
    SubmissionSession: SUBMISSION_SESSION_RULES,
    SubmissionAnswerSlot: SUBMISSION_ANSWER_SLOT_RULES,
    SubmissionEvent: SUBMISSION_EVENT_RULES,
    SurveyQuestion: SURVEY_QUESTION_RULES,
    SurveyEncryptionKey: SURVEY_ENCRYPTION_KEY_RULES,
    SurveyScoringRule: SURVEY_SCORING_RULE_RULES,
    ProjectRole: PROJECT_ROLE_RULES,
    ProjectMembership: PROJECT_MEMBERSHIP_RULES,
    SurveyMembershipRole: SURVEY_MEMBERSHIP_ROLE_RULES,
    ResponseEnvelope: RESPONSE_ENVELOPE_RULES,
    ResponseAnswer: RESPONSE_ANSWER_RULES,
}
