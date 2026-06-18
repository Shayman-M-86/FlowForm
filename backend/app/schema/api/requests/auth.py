from pydantic import BaseModel

from app.schema.api.common.fields import IdToken


class BootstrapUserRequest(BaseModel):
    """Request body for post-auth user bootstrap."""

    id_token: IdToken
