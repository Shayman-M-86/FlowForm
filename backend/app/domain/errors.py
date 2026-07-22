from typing import Any

from app.core.errors import AppError, AuthError


class ForbiddenError(AppError):
    """Error raised when a user attempts to access a resource they do not have permission for."""

    def __init__(self, message: str = "You do not have permission to access this resource.") -> None:
        super().__init__(
            status_code=403,
            code="FORBIDDEN",
            message=message,
        )


class InvalidIdTokenSubjectError(AuthError):
    """Error raised when an ID token does not contain a valid subject."""

    def __init__(self) -> None:
        super().__init__(
            message="ID token did not contain a valid subject.",
            code="INVALID_ID_TOKEN",
            status_code=401,
        )


class TokenSubjectMismatchError(AuthError):
    """Error raised when access-token and ID-token subjects do not match."""

    def __init__(self) -> None:
        super().__init__(
            message="ID token subject did not match the access token subject.",
            code="TOKEN_SUBJECT_MISMATCH",
            status_code=401,
        )


class MissingEmailClaimError(AuthError):
    """Error raised when an ID token does not contain a usable email claim."""

    def __init__(self) -> None:
        super().__init__(
            message="ID token did not contain an email claim.",
            code="MISSING_EMAIL_CLAIM",
            status_code=400,
        )


class LinkNotFoundError(AppError):
    """Error raised when a link cannot be found for a given token."""

    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="NOT_FOUND",
            message="Invalid or unknown token",
        )


class PublicLinkNotFoundError(AppError):
    """Error raised when a public link cannot be found by survey + link ID."""

    def __init__(self) -> None:
        super().__init__(status_code=404, code="NOT_FOUND", message="Survey link not found")


class LinkInactiveError(AppError):
    """Error raised when a link is found but is inactive."""

    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            code="LINK_INACTIVE",
            message="This link is inactive",
        )


class LinkExpiredError(AppError):
    """Error raised when a link is found but has expired."""

    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            code="LINK_EXPIRED",
            message="This link has expired",
        )


class LinkNoResponseError(AppError):
    """Error raised when a link does not permit submissions."""

    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            code="LINK_NO_RESPONSE",
            message="This link does not allow submissions",
        )


class LinkAssignmentMismatchError(AppError):
    """Error raised when an authenticated user does not match an assigned link."""

    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            code="LINK_ASSIGNED_TO_ANOTHER_USER",
            message="This link is assigned to a different user.",
        )


class LinkAuthAssignmentRequiredError(AppError):
    """Error raised when an authenticated link is not assigned to a participant."""

    def __init__(self) -> None:
        super().__init__(
            status_code=422,
            code="LINK_ASSIGNED_PARTICIPANT_REQUIRED",
            message="Links that require authentication must be assigned to a participant.",
        )


class LinkNoRecipientError(AppError):
    """Error raised when trying to email a link that has no assigned participant."""

    def __init__(self) -> None:
        super().__init__(
            status_code=422,
            code="LINK_NO_RECIPIENT",
            message="Cannot send email for a link without an assigned participant.",
        )


class LinkParticipantVerificationRequiredError(AppError):
    """Error raised when an authenticated link's participant is not user-linked."""

    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            code="LINK_PARTICIPANT_VERIFICATION_REQUIRED",
            message="This link's participant must complete verification before this link can be used.",
        )


class LinkAuthRequiredError(AppError):
    """Error raised when a link requires authentication but the caller is anonymous."""

    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            code="LINK_AUTH_REQUIRED",
            message="This link requires authentication.",
        )


class LinkAlreadyUsedError(AppError):
    """Error raised when a single-use link has already been consumed."""

    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            code="LINK_ALREADY_USED",
            message="This link has already been used.",
        )


class PrivateSurveyAssignedEmailRequiredError(AppError):
    """Error raised when a private survey link is not assigned to a participant."""

    def __init__(self) -> None:
        super().__init__(
            status_code=422,
            code="ASSIGNED_PARTICIPANT_REQUIRED",
            message="Private surveys require links assigned to a participant.",
        )


# Survey publish errors
class SurveyNotFoundError(AppError):
    """Error raised when a survey cannot be found for a given survey_id and project_id."""

    def __init__(self, survey_id: int, project_id: int) -> None:
        super().__init__(
            status_code=404,
            code="SURVEY_NOT_FOUND",
            message=f"Survey {survey_id} was not found in project {project_id}.",
        )

class SurveyDeletePublishedError(AppError):
    """Error raised when attempting to delete a survey that has a published version."""

    def __init__(self, survey_id: int) -> None:
        super().__init__(
            status_code=409,
            code="SURVEY_HAS_PUBLISHED_VERSION",
            message=f"Cannot delete survey {survey_id} because it has a published version.",
        )

class SurveyNotPublishedError(AppError):
    """Error raised when attempting to access a survey that has not been published."""

    def __init__(self, survey_id: int, project_id: int) -> None:
        super().__init__(
            status_code=404,
            code="SURVEY_NOT_PUBLISHED",
            message=f"Survey {survey_id} in project {project_id} is not published.",
        )


class SurveyPublishError(AppError):
    """Error raised when a survey cannot be published due to validation issues."""

    def __init__(self, message: str) -> None:
        super().__init__(
            status_code=409,
            code="SURVEY_PUBLISH_ERROR",
            message=message,
            details={"validation_errors": message},
        )


class SurveyNotFoundBySlugError(AppError):
    """Error raised when no public survey matches the given slug."""

    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="NOT_FOUND",
            message="Survey not found",
        )


class SurveyVisibilityMismatchError(AppError):
    """Error raised when a survey's visibility and public_slug fields are inconsistent.

    A survey is publicly browsable iff ``visibility == "public"`` AND
    ``public_slug`` is set. Any other combination is invalid and rejected
    before the row is committed.
    """

    def __init__(self, message: str) -> None:
        super().__init__(
            status_code=422,
            code="SURVEY_VISIBILITY_MISMATCH",
            message=message,
        )


class SurveyNotAccessibleError(AppError):
    """Error raised when a survey's visibility does not permit public access."""

    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            code="SURVEY_NOT_ACCESSIBLE",
            message="This survey is not accessible in this context.",
        )


class SurveyNoResponseStoreError(AppError):
    """Error raised when a survey has no default response store configured."""

    def __init__(self, message: str) -> None:
        super().__init__(
            status_code=400,
            code="INVALID_REQUEST",
            message=message,
        )


class ProjectNotFoundError(AppError):
    """Error raised when a project cannot be found."""

    def __init__(self, *, project_id: int | None = None, project_slug: str | None = None) -> None:
        ref = f"slug={project_slug!r}" if project_slug is not None else f"id={project_id}"
        super().__init__(
            status_code=404,
            code="NOT_FOUND",
            message=f"Project {ref} not found.",
        )


class ProjectSlugConflictError(AppError):
    """Error raised when a project slug is already taken."""

    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            code="CONFLICT",
            message="Conflict — a project with that slug already exists",
        )


class SurveySlugConflictError(AppError):
    """Error raised when a survey slug already exists within the project."""

    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            code="CONFLICT",
            message="Conflict — check slug uniqueness",
        )


class VersionNotFoundError(AppError):
    """Error raised when a survey version cannot be found."""

    def __init__(self, survey_id: int, version_number: int) -> None:
        super().__init__(
            status_code=404,
            code="NOT_FOUND",
            message=f"Version {version_number} was not found in survey {survey_id}.",
        )


class VersionAlreadyArchivedError(AppError):
    """Error raised when attempting to archive a version that is already archived."""

    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            code="VERSION_ALREADY_ARCHIVED",
            message="Version is already archived",
        )


class VersionNotPublishedError(AppError):
    """Error raised when an operation requires a published version."""

    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            code="VERSION_NOT_PUBLISHED",
            message="Version is not published",
        )


class VersionIsActivePublishedError(AppError):
    """Error raised when attempting to archive the active published version directly."""

    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            code="VERSION_IS_ACTIVE_PUBLISHED",
            message="Cannot archive the active published version directly; unpublish it first",
        )


class VersionNotEditableError(AppError):
    """Error raised when attempting to edit content on a non-draft version."""

    def __init__(self, status: str) -> None:
        super().__init__(
            status_code=409,
            code="VERSION_NOT_EDITABLE",
            message=f"Version is '{status}' — content can only be edited on draft versions",
        )


class NodeNotFoundError(AppError):
    """Error raised when a content node (question or rule) cannot be found."""

    def __init__(self) -> None:
        super().__init__(status_code=404, code="NOT_FOUND", message="Node not found")


class ScoringRuleNotFoundError(AppError):
    """Error raised when a scoring rule cannot be found."""

    def __init__(self) -> None:
        super().__init__(status_code=404, code="NOT_FOUND", message="Scoring rule not found")


class ContentKeyConflictError(AppError):
    """Error raised when a content key already exists within a version."""

    def __init__(self, message: str) -> None:
        super().__init__(status_code=409, code="CONFLICT", message=message)


class SubmissionInvalidError(AppError):
    """Error raised when a submission is invalid for any reason."""

    def __init__(
        self,
        message: str = "Submission is invalid.",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            status_code=400,
            code="INVALID_SUBMISSION",
            message=message,
            details=details or {},
        )


class SubmissionInvalidTimestampsError(AppError):
    """Error raised when a submission has invalid timestamps (e.g. started_at is after submitted_at)."""

    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            code="INVALID_SUBMISSION_TIMESTAMPS",
            message="Submission timestamps are invalid.",
        )


class SubmissionAnswersRequiredError(AppError):
    """Error raised when a submission is missing required answers."""

    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            code="SUBMISSION_ANSWERS_REQUIRED",
            message="At least one answer is required.",
        )


class SubmissionNotFoundError(AppError):
    """Error raised when a submission cannot be found."""

    def __init__(self, submission_id: int) -> None:
        super().__init__(
            status_code=404,
            code="SUBMISSION_NOT_FOUND",
            message=f"Submission {submission_id} not found.",
        )

class UserNotFoundError(AppError):
    """Error raised when a user cannot be found."""

    def __init__(self, user_id: str) -> None:
        super().__init__(
            status_code=404,
            code="USER_NOT_FOUND",
            message=f"User {user_id} not found.",
        )


class SubjectNotFoundError(AppError):
    """Error raised when a project subject cannot be found."""

    def __init__(self) -> None:
        super().__init__(status_code=404, code="SUBJECT_NOT_FOUND", message="Subject not found.")


class ParticipantNotFoundError(AppError):
    """Error raised when a project participant cannot be found."""

    def __init__(self) -> None:
        super().__init__(status_code=404, code="PARTICIPANT_NOT_FOUND", message="Participant not found.")


class ParticipantIdentityNotVerifiableError(AppError):
    """Error raised when a participant does not have an email identity to verify."""

    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            code="PARTICIPANT_IDENTITY_NOT_VERIFIABLE",
            message="Participant identity cannot be verified from an account email.",
        )


class ParticipantIdentityEmailMismatchError(AppError):
    """Error raised when the authenticated user's email does not match the participant identity."""

    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            code="PARTICIPANT_EMAIL_MISMATCH",
            message="Authenticated account email does not match the participant identity email.",
        )


class ParticipantIdentityUserMismatchError(AppError):
    """Error raised when a participant identity is already linked to another user."""

    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            code="PARTICIPANT_USER_MISMATCH",
            message="Participant identity is linked to a different authenticated user.",
        )


class InvitationNotFoundError(AppError):
    """Error raised when an invitation cannot be found."""

    def __init__(self) -> None:
        super().__init__(status_code=404, code="NOT_FOUND", message="Invitation not found.")


class InvitationAlreadyExistsError(AppError):
    """Error raised when a pending invitation already exists for an email in a project."""

    def __init__(self, email: str) -> None:
        super().__init__(
            status_code=409,
            code="INVITATION_EXISTS",
            message=f"A pending invitation already exists for {email}.",
        )


class InvitationNotPendingError(AppError):
    """Error raised when an action requires a pending invitation but it is no longer pending."""

    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            code="INVITATION_NOT_PENDING",
            message="This invitation is no longer pending.",
        )


class AlreadyAMemberError(AppError):
    """Error raised when a user is already an active member of the project."""

    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            code="ALREADY_A_MEMBER",
            message="This user is already a member of the project.",
        )


class EmailNotVerifiedError(AppError):
    """Error raised when an action requires a verified email but the actor's is not."""

    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            code="EMAIL_NOT_VERIFIED",
            message="Please verify your email address before accepting this invitation.",
        )


class ProjectRoleNotFoundError(AppError):
    """Error raised when a project role cannot be found."""

    def __init__(self) -> None:
        super().__init__(status_code=404, code="NOT_FOUND", message="Project role not found.")


class ProjectRoleSystemProtectedError(AppError):
    """Error raised when trying to mutate or delete a system role."""

    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            code="ROLE_SYSTEM_PROTECTED",
            message="System roles cannot be modified or deleted.",
        )


class MemberNotFoundError(AppError):
    """Error raised when a project membership cannot be found."""

    def __init__(self) -> None:
        super().__init__(status_code=404, code="NOT_FOUND", message="Member not found.")


class MemberSelfActionError(AppError):
    """Error raised when an actor tries to modify their own membership."""

    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            code="MEMBER_SELF_ACTION",
            message="You cannot modify your own membership.",
        )


class MemberOwnerProtectedError(AppError):
    """Error raised when trying to reassign, remove, or suspend an owner/system role."""

    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            code="MEMBER_OWNER_PROTECTED",
            message="Owner roles cannot be assigned, reassigned, removed, or suspended.",
        )


class SurveyRoleNotFoundError(AppError):
    """Error raised when a survey role cannot be found."""

    def __init__(self) -> None:
        super().__init__(status_code=404, code="NOT_FOUND", message="Survey role not found.")


class SurveyRoleNameConflictError(AppError):
    """Error raised when a survey role name is already taken within the project."""

    def __init__(self) -> None:
        super().__init__(status_code=409, code="CONFLICT", message="A survey role with that name already exists.")


class SurveyMemberRoleNotFoundError(AppError):
    """Error raised when a survey membership role assignment cannot be found."""

    def __init__(self) -> None:
        super().__init__(status_code=404, code="NOT_FOUND", message="Survey member role assignment not found.")


class SurveyMemberRoleAlreadyAssignedError(AppError):
    """Error raised when a member already has a survey role assigned for a given survey."""

    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            code="SURVEY_MEMBER_ROLE_CONFLICT",
            message="This member already has a survey role assigned for this survey.",
        )


class ManagementApiUnavailableError(AppError):
    """Error raised when the Auth0 Management API is not configured."""

    def __init__(self) -> None:
        super().__init__(
            status_code=503,
            code="MGMT_API_UNAVAILABLE",
            message="Account management is not available at this time.",
        )


class ManagementApiCallError(AppError):
    """Error raised when a call to the Auth0 Management API fails."""

    def __init__(self) -> None:
        super().__init__(
            status_code=502,
            code="MGMT_API_ERROR",
            message="Account management could not be completed at this time.",
        )


class PasswordChangeUnsupportedError(AppError):
    """Error raised when the user's identity provider cannot change passwords here."""

    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            code="PASSWORD_CHANGE_UNSUPPORTED",
            message="Password changes are not available for this sign-in method.",
        )


class SubjectResolutionError(AppError):
    """Server-invariant error: a referenced project subject could not be resolved.

    Raised when a link/identity/token points at a project_subject_id but the row
    does not resolve under the expected project. The schema's composite foreign
    keys make this unreachable today; the guard exists so a future schema change
    fails loudly instead of silently downgrading a known respondent to anonymous.
    """

    def __init__(self) -> None:
        super().__init__(
            status_code=500,
            code="SUBJECT_RESOLUTION_FAILED",
            message="A referenced respondent subject could not be resolved.",
        )


class SessionStartError(AppError):
    """Raised when session start fails during envelope creation."""

    def __init__(self, message: str = "Session start failed.") -> None:
        super().__init__(
            status_code=500,
            code="SESSION_START_FAILED",
            message=message,
        )


class SessionNotFoundError(AppError):
    """Raised when no session matches the browser resume token."""

    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="SESSION_NOT_FOUND",
            message="Session not found.",
        )


class SessionExpiredError(AppError):
    """Raised when the session has passed its expiry time."""

    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            code="SESSION_EXPIRED",
            message="This session has expired.",
        )


class SessionInvalidError(AppError):
    """Raised when the session is in an invalid state for the requested operation."""

    def __init__(self, message: str = "Session is not in a valid state.") -> None:
        super().__init__(
            status_code=409,
            code="SESSION_INVALID",
            message=message,
        )


class EnvelopeNotFoundError(AppError):
    """Raised when the response envelope cannot be found for a session locator."""

    def __init__(self) -> None:
        super().__init__(
            status_code=500,
            code="ENVELOPE_NOT_FOUND",
            message="Response envelope not found.",
        )


class AnswerSaveError(AppError):
    """Raised when an answer save operation fails."""

    def __init__(self, message: str = "Answer save failed.") -> None:
        super().__init__(
            status_code=500,
            code="ANSWER_SAVE_FAILED",
            message=message,
        )


class QuestionNotInVersionError(AppError):
    """Raised when a question node ID does not belong to the frozen survey version."""

    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            code="QUESTION_NOT_IN_VERSION",
            message="Question does not belong to this survey version.",
        )


class CompletionValidationError(AppError):
    """Raised when completion validation fails (missing required answers, etc.)."""

    def __init__(self, message: str = "Completion validation failed.") -> None:
        super().__init__(
            status_code=400,
            code="COMPLETION_VALIDATION_FAILED",
            message=message,
        )

