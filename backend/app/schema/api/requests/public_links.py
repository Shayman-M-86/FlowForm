from datetime import datetime

from pydantic import BaseModel


class CreatePublicLinkRequest(BaseModel):
    allow_response: bool = True
    expires_at: datetime | None = None


class UpdatePublicLinkRequest(BaseModel):
    is_active: bool | None = None
    allow_response: bool | None = None
    expires_at: datetime | None = None

