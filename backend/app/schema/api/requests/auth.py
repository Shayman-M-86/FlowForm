from pydantic import BaseModel


class BootstrapUserRequest(BaseModel):
    """Request body for post-auth user bootstrap."""

    id_token: str
