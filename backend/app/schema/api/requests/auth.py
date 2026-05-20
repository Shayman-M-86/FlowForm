from pydantic import BaseModel, Field, field_validator

from app.schema.api import limits


class BootstrapUserRequest(BaseModel):
    """Request body for post-auth user bootstrap."""

    id_token: str = Field(max_length=limits.ID_TOKEN_MAX)

    @field_validator("id_token")
    @classmethod
    def validate_id_token(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("id_token must not be blank.")
        return value
