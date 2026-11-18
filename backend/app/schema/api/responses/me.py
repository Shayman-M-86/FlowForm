from app.schema.api.common.base import APIResponseModel
from app.schema.api.responses.auth import CurrentUserResponses
from app.schema.models.common.types import Url


class CurrentUserProfileResponses(CurrentUserResponses):
    """Current-user identity and profile with verification state."""

    email_verified: bool


class PasswordChangeTicketResponses(APIResponseModel):
    """Hosted Auth0 password-change ticket URL."""

    ticket_url: Url


class EmailVerificationCheckResponses(APIResponseModel):
    """Result of a live, on-demand email verification check against Auth0."""

    email_verified: bool
