"""Authentication request contracts."""

from app.schema.api.common.base import APIRequestModel
from app.schema.api.common.types import IdentityToken


class BootstrapUserRequest(APIRequestModel):
    """Request body for post-auth user bootstrap."""

    id_token: IdentityToken
