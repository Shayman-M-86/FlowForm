from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectOut(BaseModel):
    """API response shape for a project."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    created_by_user_id: int | None
    created_at: datetime
