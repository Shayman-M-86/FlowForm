# app/api/utils/serialization.py

from typing import Any

from pydantic import TypeAdapter, ValidationError

from app.core.errors import ResponseValidationError


def serialize(schema: Any, value: Any) -> Any:
    """Validate and serialize a value for an API response."""
    try:
        return (
            TypeAdapter(schema)
            .validate_python(
                value,
                from_attributes=True,
            )
            .model_dump(
                mode="json",
                by_alias=True,
            )
        )

    except ValidationError as exc:
        raise ResponseValidationError(
            schema_name=getattr(schema, "__name__", repr(schema)),
            original_error=exc,
        ) from exc
