"""Canonical HTTP value types; validation constraints are defined once here."""

from typing import Annotated, Any, Literal

from pydantic import AfterValidator, AwareDatetime, Field, StringConstraints

from app.domain.permissions import ProjectPermission as ProjectPermission
from app.domain.permissions import SurveyPermission as SurveyPermission
from app.schema import limits
from app.schema.models.common.types import LimitedList, TrimmedString, Url
from app.schema.models.common.validators import validate_future_datetime_utc
from app.schema.models.submission.types import SubmissionSessionId

ProjectPermissionSet = Annotated[set[ProjectPermission], Field(description="Unique project permissions")]
SurveyPermissionSet = Annotated[set[SurveyPermission], Field(description="Unique survey permissions")]


# Value constraints live here; contracts declare defaults and requiredness.
PageNumber = Annotated[int, Field(ge=1)]
PageSize = Annotated[int, Field(ge=1, le=limits.LIST_PAGE_SIZE_MAX)]
SearchText = Annotated[str, StringConstraints(max_length=limits.DEFAULT_STRING_MAX)]
IdentityToken = Annotated[TrimmedString, Field(max_length=8192)]
AIImportPrompt = Annotated[TrimmedString, Field(max_length=4_000)]
ProfilePictureUrl = Annotated[Url, StringConstraints(strip_whitespace=True, min_length=1)]
Username = Annotated[TrimmedString, Field(max_length=128, pattern=r"^[a-zA-Z0-9_.\-]+$")]
FutureExpiry = Annotated[AwareDatetime, AfterValidator(validate_future_datetime_utc)]
SessionIdList = LimitedList[SubmissionSessionId]

CanonicalSubjectFilter = Literal["canonical", "alias", "all"]


type PageItems[T] = Annotated[list[T], Field(max_length=limits.LIST_PAGE_SIZE_MAX)]


# Error handlers emit untruncated text and extensible JSON details.
ErrorCode = Annotated[str, Field(description="Machine-readable error code")]
ErrorMessage = Annotated[str, Field(description="Human-readable error message")]
ErrorDetails = dict[str, Any]
