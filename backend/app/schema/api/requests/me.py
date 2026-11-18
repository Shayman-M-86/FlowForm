"""Profile operation constraints are local to these HTTP contracts."""

from app.schema.api.common.base import APIRequestModel
from app.schema.api.common.types import ProfilePictureUrl, Username
from app.schema.types import EmailAddress, ProfileName


class UpdateProfileRequest(APIRequestModel):
    """Update display name, nickname, and/or profile picture."""

    display_name: ProfileName | None = None
    nickname: ProfileName | None = None
    picture: ProfilePictureUrl | None = None


class ChangeEmailRequest(APIRequestModel):
    """Request body for changing the account email address."""

    email: EmailAddress


class ChangeUsernameRequest(APIRequestModel):
    """Request body for changing the Auth0 username."""

    username: Username
