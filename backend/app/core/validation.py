"""Generic Pydantic validation utilities.

Flask-free so any layer (services, email, domain) can import and use them.
"""

from __future__ import annotations

from typing import Any, overload

from pydantic import BaseModel, TypeAdapter, ValidationError

from app.core.errors import RequestValidationError


@overload
def validate[T: BaseModel](schema: type[T], data: Any) -> T: ...
@overload
def validate(schema: Any, data: Any) -> Any: ...
def validate(schema: Any, data: Any) -> Any:
    """Validate ``data`` against a Pydantic schema.

    Accepts either a ``BaseModel`` subclass or any type supported by
    ``TypeAdapter``.  Raises ``RequestValidationError`` on failure so
    the global error handler can produce a consistent 422 response.
    """
    try:
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            return schema.model_validate(data)

        return TypeAdapter(schema).validate_python(data)
    except ValidationError as exc:
        raise RequestValidationError(exc) from exc
