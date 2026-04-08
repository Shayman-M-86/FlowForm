from datetime import datetime

from pydantic import BaseModel


class CreatePublicLinkRequest(BaseModel):
    """Request body for creating a public share link for a survey."""

    allow_response: bool = True
    expires_at: datetime | None = None


class UpdatePublicLinkRequest(BaseModel):
    """Request body for partially updating a public share link."""

    is_active: bool | None = None
    allow_response: bool | None = None
    expires_at: datetime | None = None

class ResolveTokenRequest(BaseModel):
    """Request body for resolving a public link token to its associated survey and project."""
    token: str