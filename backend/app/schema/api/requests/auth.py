from pydantic import BaseModel

from app.schema.api.requests.field_types import IdToken


class BootstrapUserRequest(BaseModel):
    """Request body for post-auth user bootstrap."""

    id_token: IdToken
