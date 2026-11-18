from pydantic import ConfigDict

from app.schema.api.common.base import APIResponseModel
from app.schema.api.responses.projects import ProjectResponses
from app.schema.models.common.types import EmailAddress
from app.schema.models.identity.types import Auth0UserId, ProfileName, UserId


class CurrentUserResponses(APIResponseModel):
    """API response shape for a bootstrapped user."""

    model_config = ConfigDict(from_attributes=True)

    id: UserId
    auth0_user_id: Auth0UserId
    email: EmailAddress
    display_name: ProfileName | None


class BootstrapUserResponses(APIResponseModel):
    """API response shape for a bootstrap-user request."""

    created: bool
    user: CurrentUserResponses
    default_project: ProjectResponses | None = None
