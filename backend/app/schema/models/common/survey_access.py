"""Valid combinations of survey visibility and public access metadata."""

from typing import Annotated, Literal

from pydantic import Field

from app.schema.models.common.base import DataModel
from app.schema.types import Slug


class PublicSurveyAccess(DataModel):
    """A publicly discoverable survey requires a public slug."""

    visibility: Literal["public"]
    public_slug: Slug


class NonPublicSurveyAccess(DataModel):
    """Private and link-only surveys have no public slug."""

    visibility: Literal["private", "link_only"]
    public_slug: None = None


SurveyAccess = Annotated[
    PublicSurveyAccess | NonPublicSurveyAccess,
    Field(discriminator="visibility", title="SurveyAccess"),
]
