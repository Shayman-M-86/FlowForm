"""Reusable JSON answer values and structured matching contents."""

from typing import Annotated

from pydantic import Field, StrictBool

from app.schema.models.common.base import DataModel
from app.schema.types import (
    AnswerInteger,
    AnswerNumber,
    CalendarDate,
    ChoiceOptionUuid,
    LimitedList,
    LongString,
    MatchingMatchUuid,
    MatchingPromptUuid,
)


class MatchingPair(DataModel):
    """One prompt-to-match association."""

    prompt_uuid: MatchingPromptUuid
    match_uuid: MatchingMatchUuid


class MatchingValue(DataModel):
    """Documented matching answer structure."""

    pairs: LimitedList[MatchingPair]


ChoiceValues = LimitedList[ChoiceOptionUuid]
# No arbitrary dictionaries, recursive JSON, or null answered values.
AnswerValue = Annotated[
    LongString | AnswerInteger | AnswerNumber | StrictBool | CalendarDate | ChoiceValues | MatchingValue,
    Field(title="AnswerValue"),
]
