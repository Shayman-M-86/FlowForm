"""Canonical internal and external user identifiers, independent of HTTP."""

from typing import Annotated

from pydantic import Field, StringConstraints

from app.schema.models.common.types import DatabaseIdentity, TrimmedString

UserId = Annotated[
    DatabaseIdentity,
    Field(description="Internal users.id database identity"),
]
Auth0UserId = Annotated[
    str,
    StringConstraints(min_length=1, max_length=255),
    Field(description="Opaque external Auth0 subject; distinct from the internal user ID"),
]


ProfileName = Annotated[TrimmedString, Field(max_length=100)]
