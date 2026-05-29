from pydantic import BaseModel

from app.schema.api.requests.field_types import (
    FutureExpiresAt,
    NormalisedEmail,
    PublicLinkName,
    PublicLinkToken,
)


class CreatePublicLinkRequest(BaseModel):
    """Request body for creating a new public link."""
    name: PublicLinkName
    assigned_email: NormalisedEmail | None = None
    requires_auth: bool = False
    expires_at: FutureExpiresAt | None = None


class UpdatePublicLinkRequest(BaseModel):
    """Request body for updating a public link."""
    is_active: bool | None = None
    name: PublicLinkName | None = None
    assigned_email: NormalisedEmail | None = None
    requires_auth: bool | None = None
    expires_at: FutureExpiresAt | None = None


class ResolveTokenRequest(BaseModel):
    """Request body for resolving a public link token."""
    token: PublicLinkToken