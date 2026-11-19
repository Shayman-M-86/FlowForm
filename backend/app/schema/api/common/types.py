"""Canonical HTTP value types; validation constraints are defined once here."""

from typing import Annotated, Any

from pydantic import AfterValidator, AwareDatetime, Field, StringConstraints

from app.domain.permissions import ProjectPermission as ProjectPermission
from app.domain.permissions import SurveyPermission as SurveyPermission
from app.schema import limits
from app.schema.types import LimitedList, SubmissionSessionId, TrimmedString, Url
from app.schema.validators import validate_future_datetime_utc

type ProjectPermissionSet = Annotated[set[ProjectPermission], Field(description="Unique project permissions")]
type SurveyPermissionSet = Annotated[set[SurveyPermission], Field(description="Unique survey permissions")]


# Value constraints live here; contracts declare defaults and requiredness.
type IdentityToken = Annotated[TrimmedString, StringConstraints(max_length=8192)]
type AIImportPrompt = Annotated[TrimmedString, StringConstraints(max_length=4_000)]
type ProfilePictureUrl = Annotated[Url, StringConstraints(strip_whitespace=True, min_length=1)]
type Username = Annotated[TrimmedString, StringConstraints(max_length=128, pattern=r"^[a-zA-Z0-9_.\-]+$")]
type FutureExpiry = Annotated[AwareDatetime, AfterValidator(validate_future_datetime_utc)]
type SessionIdList = LimitedList[SubmissionSessionId]


type PageItems[T] = Annotated[list[T], Field(max_length=limits.LIST_PAGE_SIZE_MAX)]


# Error handlers emit untruncated text and extensible JSON details.
type ErrorCode = Annotated[str, Field(description="Machine-readable error code")]
type ErrorMessage = Annotated[str, Field(description="Human-readable error message")]
type ErrorDetails = dict[str, Any]
