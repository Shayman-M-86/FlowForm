from typing import Any

from app.core.errors import AppError, AuthError


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
        super().__init__(status_code=404, code="NOT_FOUND", message="Public link not found")


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


class UserBootstrapConflictError(AppError):
    """Error raised when user bootstrap conflicts with an existing local identity."""

    def __init__(self, *, email: str) -> None:
        super().__init__(
            status_code=409,
            code="CONFLICT",
            message=f"Conflict — a user with email '{email}' already exists",
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


class VersionNotEditableError(AppError):
    """Error raised when attempting to edit content on a non-draft version."""

    def __init__(self, status: str) -> None:
        super().__init__(
            status_code=409,
            code="VERSION_NOT_EDITABLE",
            message=f"Version is '{status}' — content can only be edited on draft versions",
        )


class QuestionNotFoundError(AppError):
    """Error raised when a question cannot be found."""

    def __init__(self) -> None:
        super().__init__(status_code=404, code="NOT_FOUND", message="Question not found")


class RuleNotFoundError(AppError):
    """Error raised when a rule cannot be found."""

    def __init__(self) -> None:
        super().__init__(status_code=404, code="NOT_FOUND", message="Rule not found")


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