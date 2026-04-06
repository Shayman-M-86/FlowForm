from app.core.errors import AppError


class LinkNotFoundError(AppError):
    """Error raised when a link cannot be found for a given token."""
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="NOT_FOUND",
            message="Invalid or unknown token",
        )


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

# Survey publish errors
class SurveyNotFoundError(AppError):
    """Error raised when a survey cannot be found for a given survey_id and project_id."""
    def __init__(self, survey_id: int, project_id: int) -> None:
        super().__init__(
            status_code=404,
            code="SURVEY_NOT_FOUND",
            message=f"Survey {survey_id} was not found in project {project_id}.",
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
        )




