"""Reusable constrained types; enforced when used in Pydantic validation."""

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BeforeValidator, Field, StrictBool, StrictFloat, StrictInt, StringConstraints

from app.schema import limits
from app.schema.models.common.types import DatabaseIdentity, LongString, Text, TrimmedString
from app.schema.models.common.validators import parse_calendar_date

SurveyTitle = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=200,
    ),
]


ReadableId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=128,
    ),
]

FieldPrompt = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=1000,
    ),
]

ChoiceOptionLabel = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=1000,
    ),
]


SurveyVersionId = Annotated[
    DatabaseIdentity,
    Field(description="Identity of a persisted survey version"),
]


SurveyId = Annotated[DatabaseIdentity, Field(description="Survey identity")]
SurveyRoleId = Annotated[DatabaseIdentity, Field(description="Survey role identity")]
SurveyLinkId = Annotated[UUID, Field(description="Survey access link identity")]
SurveyFieldUuid = Annotated[UUID, Field(description="Stable answerable field identity in a survey document")]
ChoiceOptionUuid = Annotated[UUID, Field(description="Stable selectable option identity")]
MatchingPromptUuid = Annotated[UUID, Field(description="Stable matching prompt identity")]
MatchingMatchUuid = Annotated[UUID, Field(description="Stable matching target identity")]
SurveyVersionNumber = Annotated[int, Field(ge=1, description="Sequential version number within a survey")]


SurveyAccessLinkName = Annotated[TrimmedString, Field(max_length=120)]

SurveyAccessToken = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=256),
]


SectionTitle = Annotated[TrimmedString, Field(max_length=200)]
NoticeTitle = Annotated[TrimmedString, Field(max_length=200)]
ContentText = Annotated[LongString, StringConstraints(min_length=1, pattern=r"\S")]
InputPlaceholder = Annotated[Text, Field(max_length=200)]
InputAffix = Annotated[Text, Field(max_length=128)]
DocumentRevision = Annotated[StrictInt, Field(ge=1)]
HeadingLevel = Annotated[StrictInt, Field(ge=1, le=6)]
NoticeTone = Literal["info", "success", "warning", "error"]
NumberPresentation = Literal["input", "stepper"]
RatingPresentation = Literal["slider", "stars", "scale"]
SingleChoicePresentation = Literal["radio", "dropdown", "buttons", "cards"]
MultipleChoicePresentation = Literal["checkboxes", "buttons", "cards"]
BooleanPresentation = Literal["yes_no", "toggle"]
DatePresentation = Literal["calendar", "input"]
OutcomeId = ReadableId


AnswerInteger = StrictInt
AnswerNumber = Annotated[StrictFloat, Field(allow_inf_nan=False)]
AnswerLength = Annotated[StrictInt, Field(ge=0)]
CalendarDate = Annotated[date, BeforeValidator(parse_calendar_date)]
ConditionScalar = LongString | AnswerInteger | AnswerNumber | StrictBool | CalendarDate
ConditionNumber = AnswerInteger | AnswerNumber
ConditionText = LongString

type SurveyBlocks[T] = Annotated[list[T], Field(max_length=limits.SURVEY_BLOCKS_MAX)]
type ConditionList[T] = Annotated[list[T], Field(min_length=1, max_length=limits.DEFAULT_COLLECTION_MAX)]

OrderedConditionValue = ConditionNumber | CalendarDate
