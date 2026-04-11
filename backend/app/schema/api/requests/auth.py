from pydantic import BaseModel, field_validator


class BootstrapUserRequest(BaseModel):
    """Request body for post-auth user bootstrap."""

    id_token: str

    @field_validator("id_token")
    @classmethod
    def validate_id_token(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("id_token must not be blank.")
        return value
