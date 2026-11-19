"""Authoritative shared value types across application, validation, and persistence.

NewType establishes static identity; Annotated supplies boundary validation.
String rules use StringConstraints; numeric and collection rules use Field.
Neither annotations nor NewType calls validate ordinary Python assignments.
"""

from datetime import date, datetime
from typing import Annotated, NewType
from uuid import UUID

from pydantic import BeforeValidator, EmailStr, Field, StrictBool, StrictFloat, StrictInt, StringConstraints

from app.domain.permissions import PermissionName as PermissionName
from app.schema import limits
from app.schema.validators import normalise_email, parse_calendar_date

# Shared metadata is immutable by convention. Defaults and property aliases belong
# to models, not these reusable value constraints.
DATABASE_ID_CONSTRAINTS = Field(ge=1, le=limits.BIGINT_ID_MAX)
COLLECTION_CONSTRAINTS = Field(max_length=limits.DEFAULT_COLLECTION_MAX)

# Generic values

type ShortString = Annotated[str, StringConstraints(max_length=limits.SHORT_STRING_MAX)]

type LongString = Annotated[str, StringConstraints(max_length=limits.LONG_STRING_MAX)]

type LimitedList[T] = Annotated[list[T], COLLECTION_CONSTRAINTS]

type LimitedDict[T] = Annotated[dict[str, T], COLLECTION_CONSTRAINTS]

type TrimmedString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

type DatabaseIdentity = Annotated[int, DATABASE_ID_CONSTRAINTS]

type Timestamp = Annotated[datetime, Field(description="Recorded timestamp supplied by the owning operation")]

type Count = Annotated[int, Field(ge=0)]

type PageNumber = Annotated[int, Field(ge=1)]
type PageSize = Annotated[int, Field(ge=1, le=limits.LIST_PAGE_SIZE_MAX)]

type Text = Annotated[str, StringConstraints(max_length=limits.DEFAULT_STRING_MAX)]

type SearchText = Annotated[str, StringConstraints(max_length=limits.DEFAULT_STRING_MAX)]

type Url = Annotated[str, StringConstraints(max_length=2048)]

type EmailAddress = Annotated[EmailStr, BeforeValidator(normalise_email), StringConstraints(max_length=254)]

type Slug = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=limits.SLUG_MAX,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    ),
]


# Accounts and identity

_UserId = NewType("_UserId", int)
type UserId = Annotated[_UserId, DATABASE_ID_CONSTRAINTS, Field(description="Internal users.id database identity")]

_Auth0UserId = NewType("_Auth0UserId", str)
type Auth0UserId = Annotated[
    _Auth0UserId,
    StringConstraints(min_length=1, max_length=255),
    Field(description="Opaque external Auth0 subject; distinct from the internal user ID"),
]

type ProfileName = Annotated[TrimmedString, StringConstraints(max_length=100)]


# Projects and participants

type ProjectName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=100,
    ),
]

_ProjectId = NewType("_ProjectId", int)
type ProjectId = Annotated[_ProjectId, DATABASE_ID_CONSTRAINTS, Field(description="Project identity")]

_ProjectRoleId = NewType("_ProjectRoleId", int)
type ProjectRoleId = Annotated[_ProjectRoleId, DATABASE_ID_CONSTRAINTS, Field(description="Project role identity")]

_ProjectMembershipId = NewType("_ProjectMembershipId", int)
type ProjectMembershipId = Annotated[
    _ProjectMembershipId, DATABASE_ID_CONSTRAINTS, Field(description="Project membership identity")
]

_ProjectInvitationId = NewType("_ProjectInvitationId", int)
type ProjectInvitationId = Annotated[
    _ProjectInvitationId, DATABASE_ID_CONSTRAINTS, Field(description="Project invitation identity")
]

_SubjectId = NewType("_SubjectId", UUID)
type SubjectId = Annotated[_SubjectId, Field(description="Project subject identity")]

_SubjectIdentityId = NewType("_SubjectIdentityId", UUID)
type SubjectIdentityId = Annotated[_SubjectIdentityId, Field(description="Identity attached to a project subject")]

_ParticipantId = NewType("_ParticipantId", UUID)
type ParticipantId = Annotated[_ParticipantId, Field(description="Project participant identity")]

type RoleName = Annotated[TrimmedString, StringConstraints(max_length=80)]

type RoleDescription = Annotated[TrimmedString, StringConstraints(max_length=500)]

type InvitationMessage = Annotated[TrimmedString, StringConstraints(max_length=500)]

type SubjectCode = Annotated[TrimmedString, StringConstraints(max_length=128)]


# Survey values

type SurveyTitle = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=200,
    ),
]

type ReadableId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=128,
    ),
]

type FieldPrompt = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=1000,
    ),
]

type ChoiceOptionLabel = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=1000,
    ),
]

_SurveyVersionId = NewType("_SurveyVersionId", int)
type SurveyVersionId = Annotated[
    _SurveyVersionId, DATABASE_ID_CONSTRAINTS, Field(description="Identity of a persisted survey version")
]

_SurveyId = NewType("_SurveyId", int)
type SurveyId = Annotated[_SurveyId, DATABASE_ID_CONSTRAINTS, Field(description="Survey identity")]

_SurveyRoleId = NewType("_SurveyRoleId", int)
type SurveyRoleId = Annotated[_SurveyRoleId, DATABASE_ID_CONSTRAINTS, Field(description="Survey role identity")]

_SurveyLinkId = NewType("_SurveyLinkId", UUID)
type SurveyLinkId = Annotated[_SurveyLinkId, Field(description="Survey access link identity")]

_SurveyFieldUuid = NewType("_SurveyFieldUuid", UUID)
type SurveyFieldUuid = Annotated[
    _SurveyFieldUuid, Field(description="Stable answerable field identity in a survey document")
]

_ChoiceOptionUuid = NewType("_ChoiceOptionUuid", UUID)
type ChoiceOptionUuid = Annotated[_ChoiceOptionUuid, Field(description="Stable selectable option identity")]

_MatchingPromptUuid = NewType("_MatchingPromptUuid", UUID)
type MatchingPromptUuid = Annotated[_MatchingPromptUuid, Field(description="Stable matching prompt identity")]

_MatchingMatchUuid = NewType("_MatchingMatchUuid", UUID)
type MatchingMatchUuid = Annotated[_MatchingMatchUuid, Field(description="Stable matching target identity")]

type SurveyVersionNumber = Annotated[int, Field(ge=1, description="Sequential version number within a survey")]

type SurveyAccessLinkName = Annotated[TrimmedString, StringConstraints(max_length=120)]

type SurveyAccessToken = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=256),
]

type SectionTitle = Annotated[TrimmedString, StringConstraints(max_length=200)]

type NoticeTitle = Annotated[TrimmedString, StringConstraints(max_length=200)]

type ContentText = Annotated[LongString, StringConstraints(min_length=1, pattern=r"\S")]

type InputPlaceholder = Annotated[Text, StringConstraints(max_length=200)]

type InputAffix = Annotated[Text, StringConstraints(max_length=128)]

type DocumentRevision = Annotated[StrictInt, Field(ge=1)]

type HeadingLevel = Annotated[StrictInt, Field(ge=1, le=6)]

type OutcomeId = ReadableId

type AnswerInteger = StrictInt

type AnswerNumber = Annotated[StrictFloat, Field(allow_inf_nan=False)]

type AnswerLength = Annotated[StrictInt, Field(ge=0)]

type CalendarDate = Annotated[date, BeforeValidator(parse_calendar_date)]

type ConditionScalar = LongString | AnswerInteger | AnswerNumber | StrictBool | CalendarDate

type ConditionNumber = AnswerInteger | AnswerNumber

type ConditionText = LongString

type SurveyBlocks[T] = Annotated[list[T], Field(max_length=limits.SURVEY_BLOCKS_MAX)]

type ConditionList[T] = Annotated[list[T], COLLECTION_CONSTRAINTS, Field(min_length=1)]

type OrderedConditionValue = ConditionNumber | CalendarDate


# Submissions

_ClientMutationId = NewType("_ClientMutationId", UUID)
type ClientMutationId = Annotated[_ClientMutationId, Field(description="Identity of a client answer mutation")]

_SubmissionSessionId = NewType("_SubmissionSessionId", UUID)
type SubmissionSessionId = Annotated[_SubmissionSessionId, Field(description="Respondent submission session identity")]

type AnswerList[T] = Annotated[list[T], Field(description="Saved answers belonging to the session")]


# Response stores

_ResponseStoreId = NewType("_ResponseStoreId", int)
type ResponseStoreId = Annotated[
    _ResponseStoreId, DATABASE_ID_CONSTRAINTS, Field(description="Response store identity")
]


# Cryptographic values are static labels over bytes, without Pydantic constraints.
# Keep plaintext, wrapped material, and pseudonymous locators distinct.

PlaintextSurveyKey = NewType("PlaintextSurveyKey", bytes)
WrappedSurveyKey = NewType("WrappedSurveyKey", bytes)
PlaintextSessionKey = NewType("PlaintextSessionKey", bytes)
WrappedSessionKey = NewType("WrappedSessionKey", bytes)
SessionLocator = NewType("SessionLocator", bytes)
AnswerLocator = NewType("AnswerLocator", bytes)
