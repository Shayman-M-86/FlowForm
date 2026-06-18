from pydantic import BaseModel

from app.schema.api.common.fields import AccountEmail, DisplayName, Nickname, PictureUrl, Username


class UpdateProfileRequest(BaseModel):
    """Update display name, nickname, and/or profile picture."""

    display_name: DisplayName | None = None
    nickname: Nickname | None = None
    picture: PictureUrl | None = None


class ChangeEmailRequest(BaseModel):
    """Request body for changing the account email address."""

    email: AccountEmail


class ChangeUsernameRequest(BaseModel):
    """Request body for changing the Auth0 username."""

    username: Username
