from typing import Literal

from pydantic import BaseModel, model_validator


class CreateSurveyRequest(BaseModel):
    title: str
    visibility: Literal["private", "link_only", "public"] = "private"
    allow_public_responses: bool = False
    public_slug: str | None = None
    default_response_store_id: int | None = None

    @model_validator(mode="after")
    def check_visibility_constraints(self) -> "CreateSurveyRequest":
        if self.visibility == "public" and not self.public_slug:
            raise ValueError("public_slug is required when visibility is 'public'")
        if self.allow_public_responses and self.visibility not in ("link_only", "public"):
            raise ValueError("allow_public_responses requires visibility 'link_only' or 'public'")
        if self.public_slug and self.visibility not in ("link_only", "public"):
            raise ValueError("public_slug requires visibility 'link_only' or 'public'")
        return self


class UpdateSurveyRequest(BaseModel):
    title: str | None = None
    visibility: Literal["private", "link_only", "public"] | None = None
    allow_public_responses: bool | None = None
    public_slug: str | None = None
    default_response_store_id: int | None = None


class CreateVersionRequest(BaseModel):
    pass
