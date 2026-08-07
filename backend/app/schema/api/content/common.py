"""Shared primitives for survey definition content."""

import datetime
import math
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints
from pydantic.alias_generators import to_camel

from app.schema.api import limits


class ContentModel(BaseModel):
    """Base for every model inside a survey definition."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        strict=True,
        populate_by_name=True,
    )


def _identifier(prefix: str) -> StringConstraints:
    return StringConstraints(
        min_length=len(prefix) + 1,
        max_length=limits.SCHEMA_ID_MAX,
        pattern=rf"^{prefix}_[A-Za-z0-9_]+$",
    )


SectionId = Annotated[str, _identifier("section")]
BlockId = Annotated[str, _identifier("block")]
FieldId = Annotated[str, _identifier("field")]
OptionId = Annotated[str, _identifier("option")]

FieldKey = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[a-z0-9_]{1,64}$")]

ShortText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=limits.SHORT_TEXT_MAX),
]
RequiredShortText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=limits.SHORT_TEXT_MAX,
    ),
]
LongText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=limits.LONG_TEXT_MAX),
]
RequiredLongText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=limits.LONG_TEXT_MAX,
    ),
]


def _reject_non_finite(value: int | float) -> int | float:
    # json.loads accepts NaN and infinities by default, and each poisons every
    # comparison and arithmetic step downstream.
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Value must be a finite number.")
    return value


def _validate_image_url(value: str) -> str:
    if value and urlsplit(value).scheme.lower() not in {"https", "data"}:
        raise ValueError("Image URL scheme must be one of: data, https.")
    return value


# int | float rather than float: under strict mode a float field rejects the JSON
# number 1, which slider and numeric bounds legitimately carry.
NumberValue = Annotated[int | float, AfterValidator(_reject_non_finite)]

UrlText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=limits.URL_MAX),
    AfterValidator(_validate_image_url),
]

# JSON has no date type, so bounds arrive as ISO strings that strict mode would reject.
# This opt-out still refuses malformed dates, and numbers are not read as ordinals.
IsoDate = Annotated[datetime.date, Field(strict=False)]

Revision = Annotated[int, Field(ge=0, le=limits.INT_ID_MAX)]
