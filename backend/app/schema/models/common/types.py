"""Reusable constrained types; enforced when used in Pydantic validation."""

from datetime import datetime
from typing import Annotated

from pydantic import BeforeValidator, EmailStr, Field, StringConstraints

from app.schema import limits
from app.schema.models.common.validators import normalise_email

ShortString = Annotated[str, StringConstraints(max_length=limits.SHORT_STRING_MAX)]
LongString = Annotated[str, StringConstraints(max_length=limits.LONG_STRING_MAX)]

type LimitedList[T] = Annotated[list[T], Field(max_length=limits.DEFAULT_COLLECTION_MAX)]
type LimitedDict[T] = Annotated[dict[str, T], Field(max_length=limits.DEFAULT_COLLECTION_MAX)]


TrimmedString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


# Primitive representations shared by semantic domain types.
DatabaseIdentity = Annotated[int, Field(ge=1, le=limits.BIGINT_ID_MAX)]
Timestamp = Annotated[datetime, Field(description="Recorded timestamp supplied by the owning operation")]
Count = Annotated[int, Field(ge=0)]
Text = Annotated[str, StringConstraints(max_length=limits.DEFAULT_STRING_MAX)]
Url = Annotated[str, StringConstraints(max_length=2048)]


EmailAddress = Annotated[EmailStr, BeforeValidator(normalise_email), Field(max_length=254)]

Slug = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=limits.SLUG_MAX,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    ),
]
