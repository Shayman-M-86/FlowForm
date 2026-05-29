from pydantic import BaseModel, ConfigDict

from app.schema.api.responses.projects import ProjectResponses


class CurrentUserResponses(BaseModel):
    """API response shape for a bootstrapped user."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    auth0_user_id: str
    email: str
    display_name: str | None


class BootstrapUserResponses(BaseModel):
    """API response shape for a bootstrap-user request."""

    created: bool
    user: CurrentUserResponses
    default_project: ProjectResponses | None = None
