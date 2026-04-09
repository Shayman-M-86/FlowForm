from pydantic import BaseModel


class CreateProjectRequest(BaseModel):
    """Request body for creating a new project."""

    name: str
    slug: str
