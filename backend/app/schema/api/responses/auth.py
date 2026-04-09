from pydantic import BaseModel, ConfigDict


class CurrentUserOut(BaseModel):
    """API response shape for a bootstrapped user."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    auth0_user_id: str
    email: str
    display_name: str | None


class BootstrapUserOut(BaseModel):
    """API response shape for a bootstrap-user request."""

    created: bool
    user: CurrentUserOut
