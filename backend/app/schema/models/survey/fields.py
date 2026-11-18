"""Answerable fields, selectable options, and input presentation."""

from typing import Annotated, Literal

from pydantic import Field

from app.schema.models.common.base import DataModel
from app.schema.models.common.types import LimitedList, LongString
from app.schema.models.survey.answer_spec import AnswerSpec
from app.schema.models.survey.conditions import FieldBehaviour
from app.schema.models.survey.types import (
    BooleanPresentation,
    ChoiceOptionLabel,
    ChoiceOptionUuid,
    DatePresentation,
    FieldPrompt,
    InputAffix,
    InputPlaceholder,
    MultipleChoicePresentation,
    NumberPresentation,
    RatingPresentation,
    ReadableId,
    SingleChoicePresentation,
    SurveyFieldUuid,
)


class ChoiceOption(DataModel):
    """A readable option identifier and its stable machine identity."""

    id: ReadableId
    uuid: ChoiceOptionUuid
    label: ChoiceOptionLabel


class TextInteraction(DataModel):
    """Text input presentation."""

    kind: Literal["short_text", "long_text"]
    placeholder: InputPlaceholder | None = None


class NumberInteraction(DataModel):
    """Numeric input presentation."""

    kind: Literal["number"]
    presentation: NumberPresentation | None = None
    prefix: InputAffix | None = None
    suffix: InputAffix | None = None


class RatingInteraction(DataModel):
    """Rating input presentation."""

    kind: Literal["rating"]
    presentation: RatingPresentation | None = None
    prefix: InputAffix | None = None
    suffix: InputAffix | None = None


class SingleChoiceInteraction(DataModel):
    """Presentation and options for a single selection."""

    kind: Literal["single_choice"]
    presentation: SingleChoicePresentation | None = None
    options: LimitedList[ChoiceOption]


class MultipleChoiceInteraction(DataModel):
    """Presentation and options for multiple selections."""

    kind: Literal["multiple_choice"]
    presentation: MultipleChoicePresentation | None = None
    options: LimitedList[ChoiceOption]


class BooleanInteraction(DataModel):
    """Boolean input presentation."""

    kind: Literal["boolean"]
    presentation: BooleanPresentation | None = None


class DateInteraction(DataModel):
    """Calendar date input presentation."""

    kind: Literal["date"]
    presentation: DatePresentation | None = None


Interaction = Annotated[
    TextInteraction
    | NumberInteraction
    | RatingInteraction
    | SingleChoiceInteraction
    | MultipleChoiceInteraction
    | BooleanInteraction
    | DateInteraction,
    Field(discriminator="kind", title="FieldInteraction"),
]


class SurveyField(DataModel):
    """An answerable field with separate presentation and accepted value data."""

    id: ReadableId
    uuid: SurveyFieldUuid
    prompt: FieldPrompt
    description: LongString | None = None
    interaction: Interaction
    answerSpec: AnswerSpec
    behaviour: FieldBehaviour | None = None
