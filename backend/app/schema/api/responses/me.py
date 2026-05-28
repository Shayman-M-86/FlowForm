from pydantic import BaseModel, ConfigDict, Field

from app.schema.api import limits


class CurrentUserProfileOut(BaseModel):
    """API response shape for the current user's profile."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    auth0_user_id: str
    email: str
    display_name: str | None
    email_verified: bool


class PasswordChangeTicketOut(BaseModel):
    """Hosted Auth0 password-change ticket URL."""

    ticket_url: str = Field(max_length=limits.URL_MAX)
