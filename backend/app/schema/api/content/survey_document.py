"""The survey document definition: the portable content of a survey version.

One canonical model, used while editing, saving, loading, previewing and publishing.
"Draft" is a lifecycle state of the version row, not a different JSON type, so lifecycle
metadata (id, status, revision, timestamps, the survey title) stays outside.

Validation splits along what a single object can see:

- An object that contradicts itself is rejected here. ``min`` above ``max`` needs no
  reference to anything else to be wrong.
- Required content and compatible interaction/response pairs are rejected here too;
  every saved definition has the same complete structural contract.
- Only checks needing the whole document — global uniqueness, unresolved references,
  operator compatibility and dependency cycles — belong to publication validation.
"""

import datetime
from typing import Annotated, Literal, Self

from pydantic import Field, StringConstraints, TypeAdapter, model_validator

from app.schema.api import limits
from app.schema.api.content.common import (
    BlockId,
    ContentModel,
    FieldId,
    FieldKey,
    IsoDate,
    LongText,
    NumberValue,
    OptionId,
    RequiredLongText,
    RequiredShortText,
    SectionId,
    ShortText,
    UrlText,
)
from app.schema.enums import (
    SURVEY_PRESENCE_OPERATORS,
    SURVEY_VALUE_TAKING_OPERATORS,
    SurveyConditionOperator,
    SurveyInteractionKind,
    SurveyResponseType,
    SurveyStringFormat,
)

SurveyDocumentStringAnswer = Annotated[
    str,
    StringConstraints(max_length=limits.RESPONSE_TEXT_MAX),
]
SurveyDocumentIntegerAnswer = Annotated[
    int,
    Field(ge=limits.RESPONSE_NUMBER_MIN, le=limits.RESPONSE_NUMBER_MAX),
]
SurveyDocumentDecimalAnswer = Annotated[
    NumberValue,
    Field(ge=limits.RESPONSE_NUMBER_MIN, le=limits.RESPONSE_NUMBER_MAX),
]
SurveyDocumentChoiceSetAnswer = Annotated[
    list[OptionId],
    Field(max_length=limits.CHOICE_OPTIONS_MAX),
]
SurveyDocumentAnswerValue = (
    SurveyDocumentStringAnswer
    | SurveyDocumentIntegerAnswer
    | SurveyDocumentDecimalAnswer
    | datetime.date
    | OptionId
    | SurveyDocumentChoiceSetAnswer
)

_SURVEY_DOCUMENT_ANSWER_ADAPTERS: dict[SurveyResponseType, TypeAdapter] = {
    "string": TypeAdapter(SurveyDocumentStringAnswer),
    "integer": TypeAdapter(SurveyDocumentIntegerAnswer),
    "decimal": TypeAdapter(SurveyDocumentDecimalAnswer),
    "date": TypeAdapter(IsoDate),
    "choice": TypeAdapter(OptionId),
    "choice_set": TypeAdapter(SurveyDocumentChoiceSetAnswer),
}


def parse_survey_document_answer_value(
    response_type: SurveyResponseType,
    value: object,
) -> SurveyDocumentAnswerValue:
    """Validate a stored value against its survey document response type."""
    # JSON has no native date value; that one response type must parse its ISO string.
    strict = response_type != "date"
    return _SURVEY_DOCUMENT_ANSWER_ADAPTERS[response_type].validate_python(value, strict=strict)


# ── Interactions ──────────────────────────────────────────────────────────────


class ChoiceOption(ContentModel):
    """One selectable option. The id is what an answer stores."""

    id: OptionId
    label: RequiredShortText


class TextInteraction(ContentModel):
    """A single-line text input."""

    kind: Literal["text"]
    presentation: Literal["plain", "email", "url", "tel"] = "plain"
    placeholder: ShortText = ""


class LongTextInteraction(ContentModel):
    """A multi-line text input."""

    kind: Literal["long_text"]
    rows: int = Field(default=4, ge=limits.LONG_TEXT_ROWS_MIN, le=limits.LONG_TEXT_ROWS_MAX)
    placeholder: ShortText = ""


class NumberInteraction(ContentModel):
    """A numeric input."""

    kind: Literal["number"]
    suffix: ShortText = ""
    placeholder: ShortText = ""


class SingleChoiceInteraction(ContentModel):
    """Select exactly one option."""

    kind: Literal["single_choice"]
    presentation: Literal["radio", "cards", "dropdown"] = "radio"
    options: list[ChoiceOption] = Field(
        min_length=1,
        max_length=limits.CHOICE_OPTIONS_MAX,
    )

    @model_validator(mode="after")
    def validate_unique_option_ids(self) -> Self:
        _validate_unique_option_ids(self.options)
        return self


class MultipleChoiceInteraction(ContentModel):
    """Select any number of options."""

    kind: Literal["multiple_choice"]
    presentation: Literal["checkbox", "cards"] = "checkbox"
    options: list[ChoiceOption] = Field(
        min_length=1,
        max_length=limits.CHOICE_OPTIONS_MAX,
    )

    @model_validator(mode="after")
    def validate_unique_option_ids(self) -> Self:
        _validate_unique_option_ids(self.options)
        return self


class RatingInteraction(ContentModel):
    """A discrete scale between two bounds."""

    kind: Literal["rating"]
    presentation: Literal["numbers", "stars", "emoji"] = "numbers"
    min: int = Field(default=1, ge=limits.RATING_BOUND_MIN, le=limits.RATING_BOUND_MAX)
    max: int = Field(default=5, ge=limits.RATING_BOUND_MIN, le=limits.RATING_BOUND_MAX)
    min_label: ShortText = ""
    max_label: ShortText = ""

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.min >= self.max:
            raise ValueError("rating min must be below max")
        return self


class SliderInteraction(ContentModel):
    """A continuous scale dragged between two bounds."""

    kind: Literal["slider"]
    min: NumberValue = 0
    max: NumberValue = 100
    step: NumberValue = Field(default=1, gt=0)
    show_value: bool = True
    min_label: ShortText = ""
    max_label: ShortText = ""

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.min >= self.max:
            raise ValueError("slider min must be below max")
        if self.step > self.max - self.min:
            raise ValueError("slider step must fit within its range")
        return self


class DateInteraction(ContentModel):
    """A date picker."""

    kind: Literal["date"]
    placeholder: ShortText = ""


FieldInteraction = Annotated[
    TextInteraction
    | LongTextInteraction
    | NumberInteraction
    | SingleChoiceInteraction
    | MultipleChoiceInteraction
    | RatingInteraction
    | SliderInteraction
    | DateInteraction,
    Field(discriminator="kind"),
]

ChoiceInteraction = SingleChoiceInteraction | MultipleChoiceInteraction


def _validate_unique_option_ids(options: list[ChoiceOption]) -> None:
    ids = [option.id for option in options]
    if len(ids) != len(set(ids)):
        raise ValueError("choice option ids must be unique")


# ── Response contracts ────────────────────────────────────────────────────────


class StringValidation(ContentModel):
    """Bounds for a free-text answer."""

    min_length: int | None = Field(default=None, ge=0, le=limits.RESPONSE_TEXT_MAX)
    max_length: int | None = Field(default=None, ge=0, le=limits.RESPONSE_TEXT_MAX)
    format: SurveyStringFormat | None = None

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.min_length is not None and self.max_length is not None and self.min_length > self.max_length:
            raise ValueError("min_length cannot be greater than max_length")
        return self


class NumberValidation(ContentModel):
    """Bounds for a numeric answer."""

    min: NumberValue | None = Field(default=None, ge=limits.RESPONSE_NUMBER_MIN, le=limits.RESPONSE_NUMBER_MAX)
    max: NumberValue | None = Field(default=None, ge=limits.RESPONSE_NUMBER_MIN, le=limits.RESPONSE_NUMBER_MAX)

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("min cannot be greater than max")
        return self


class DateValidation(ContentModel):
    """Bounds for a date answer."""

    earliest: IsoDate | None = None
    latest: IsoDate | None = None

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.earliest is not None and self.latest is not None and self.earliest > self.latest:
            raise ValueError("earliest cannot be after latest")
        return self


class ChoiceSetValidation(ContentModel):
    """Selection-count bounds for a multi-select answer."""

    min_selections: int | None = Field(default=None, ge=0, le=limits.CHOICE_OPTIONS_MAX)
    max_selections: int | None = Field(default=None, ge=1, le=limits.CHOICE_OPTIONS_MAX)

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if (
            self.min_selections is not None
            and self.max_selections is not None
            and self.min_selections > self.max_selections
        ):
            raise ValueError("min_selections cannot be greater than max_selections")
        return self


class StringResponse(ContentModel):
    """Stores free text."""

    type: Literal["string"]
    required: bool = False
    validation: StringValidation | None = None


class IntegerResponse(ContentModel):
    """Stores a whole number."""

    type: Literal["integer"]
    required: bool = False
    validation: NumberValidation | None = None


class DecimalResponse(ContentModel):
    """Stores a number that may have a fractional part."""

    type: Literal["decimal"]
    required: bool = False
    validation: NumberValidation | None = None


class DateResponse(ContentModel):
    """Stores a calendar date."""

    type: Literal["date"]
    required: bool = False
    validation: DateValidation | None = None


class ChoiceResponse(ContentModel):
    """Stores a single selected option id."""

    type: Literal["choice"]
    required: bool = False


class ChoiceSetResponse(ContentModel):
    """Stores zero or more selected option ids."""

    type: Literal["choice_set"]
    required: bool = False
    validation: ChoiceSetValidation | None = None


ResponseContract = Annotated[
    StringResponse | IntegerResponse | DecimalResponse | DateResponse | ChoiceResponse | ChoiceSetResponse,
    Field(discriminator="type"),
]


# ── Behaviour ─────────────────────────────────────────────────────────────────

ConditionValue = bool | NumberValue | str | None


class FieldAnswerCondition(ContentModel):
    """A predicate over a single field's stored answer."""

    field_id: FieldId
    operator: SurveyConditionOperator
    # bool precedes NumberValue so ``true`` stays boolean rather than binding as 1.
    value: ConditionValue = None

    @model_validator(mode="after")
    def validate_operator_value(self) -> Self:
        if self.operator in SURVEY_VALUE_TAKING_OPERATORS and self.value is None:
            raise ValueError(f"operator {self.operator!r} requires a value")
        if self.operator in SURVEY_PRESENCE_OPERATORS and self.value is not None:
            raise ValueError(f"operator {self.operator!r} does not accept a value")
        return self


class AlwaysVisible(ContentModel):
    """The field is always shown."""

    mode: Literal["always"]


class ConditionalVisibility(ContentModel):
    """The field is shown only when its condition holds."""

    mode: Literal["conditional"]
    condition: FieldAnswerCondition


FieldVisibility = Annotated[AlwaysVisible | ConditionalVisibility, Field(discriminator="mode")]


def _always_visible() -> AlwaysVisible:
    return AlwaysVisible(mode="always")


class FieldBehaviour(ContentModel):
    """Runtime behaviour attached to a field."""

    visibility: FieldVisibility = Field(default_factory=_always_visible)


# ── Fields and blocks ─────────────────────────────────────────────────────────


class SurveyField(ContentModel):
    """A question: its prompt, how it is answered, and what it stores.

    ``id`` is the answer-storage identity; ``key`` names the column in exported results.
    Interaction and response remain separate unions. A small validator enforces their
    compatibility without multiplying the model count into one class per pairing.
    """

    id: FieldId
    key: FieldKey
    prompt: RequiredShortText
    description: LongText = ""
    help_text: ShortText = ""
    interaction: FieldInteraction
    response: ResponseContract
    behaviour: FieldBehaviour = Field(default_factory=FieldBehaviour)

    @model_validator(mode="after")
    def validate_interaction_response(self) -> Self:
        allowed = _ALLOWED_RESPONSES[self.interaction.kind]
        if self.response.type not in allowed:
            expected = ", ".join(sorted(allowed))
            raise ValueError(f"{self.interaction.kind} interaction requires one of these response types: {expected}")

        if (
            isinstance(self.interaction, MultipleChoiceInteraction)
            and isinstance(self.response, ChoiceSetResponse)
            and self.response.validation is not None
        ):
            validation = self.response.validation
            option_count = len(self.interaction.options)
            if validation.min_selections is not None and validation.min_selections > option_count:
                raise ValueError("min_selections cannot exceed the number of options")
            if validation.max_selections is not None and validation.max_selections > option_count:
                raise ValueError("max_selections cannot exceed the number of options")

        if isinstance(self.interaction, SliderInteraction) and isinstance(self.response, IntegerResponse):
            values = (self.interaction.min, self.interaction.max, self.interaction.step)
            if any(not float(value).is_integer() for value in values):
                raise ValueError("an integer slider must use integral min, max and step values")

        _validate_response_bounds_against_interaction(self)
        return self


_ALLOWED_RESPONSES: dict[SurveyInteractionKind, frozenset[SurveyResponseType]] = {
    "text": frozenset({"string"}),
    "long_text": frozenset({"string"}),
    "number": frozenset({"integer", "decimal"}),
    "single_choice": frozenset({"choice"}),
    "multiple_choice": frozenset({"choice_set"}),
    "rating": frozenset({"integer"}),
    "slider": frozenset({"integer", "decimal"}),
    "date": frozenset({"date"}),
}


def _validate_response_bounds_against_interaction(field: SurveyField) -> None:
    interaction = field.interaction
    response = field.response
    validation = getattr(response, "validation", None)
    if not isinstance(interaction, RatingInteraction | SliderInteraction):
        return
    if not isinstance(validation, NumberValidation):
        return
    if validation.min is not None and validation.min < interaction.min:
        raise ValueError("response minimum cannot be below the interaction minimum")
    if validation.max is not None and validation.max > interaction.max:
        raise ValueError("response maximum cannot exceed the interaction maximum")


class HeadingContent(ContentModel):
    """Section heading payload."""

    text: RequiredShortText
    level: int = Field(default=1, ge=limits.HEADING_LEVEL_MIN, le=limits.HEADING_LEVEL_MAX)


class ParagraphContent(ContentModel):
    """Body copy payload."""

    text: RequiredLongText


class NoticeContent(ContentModel):
    """Callout payload."""

    tone: Literal["information", "success", "warning", "danger"] = "information"
    title: RequiredShortText
    text: RequiredLongText


class ImageContent(ContentModel):
    """Image payload. The url is restricted to https/data so it stays renderable."""

    url: UrlText
    alt_text: RequiredShortText
    caption: ShortText = ""


class HeadingBlock(ContentModel):
    """A heading rendered above surrounding content."""

    id: BlockId
    type: Literal["heading"]
    content: HeadingContent


class ParagraphBlock(ContentModel):
    """A block of body copy."""

    id: BlockId
    type: Literal["paragraph"]
    content: ParagraphContent


class NoticeBlock(ContentModel):
    """A callout block."""

    id: BlockId
    type: Literal["notice"]
    content: NoticeContent


class ImageBlock(ContentModel):
    """An image block."""

    id: BlockId
    type: Literal["image"]
    content: ImageContent


class DividerBlock(ContentModel):
    """A horizontal rule."""

    id: BlockId
    type: Literal["divider"]


class InputBlock(ContentModel):
    """A block that collects an answer."""

    id: BlockId
    type: Literal["input"]
    field: SurveyField


SurveyBlock = Annotated[
    HeadingBlock | ParagraphBlock | NoticeBlock | ImageBlock | DividerBlock | InputBlock,
    Field(discriminator="type"),
]


# ── Document ──────────────────────────────────────────────────────────────────


class SurveySection(ContentModel):
    """One page of the survey. List order is the order respondents see."""

    id: SectionId
    title: RequiredShortText
    description: LongText = ""
    blocks: list[SurveyBlock] = Field(
        min_length=1,
        max_length=limits.BLOCKS_PER_SECTION_MAX,
    )


class SurveyDocument(ContentModel):
    """The ordered sections of a survey version."""

    sections: list[SurveySection] = Field(
        min_length=1,
        max_length=limits.SECTIONS_MAX,
    )


class SurveyDefinition(ContentModel):
    """The complete portable content of a survey version."""

    schema_version: Literal[1] = 1
    document: SurveyDocument

    @model_validator(mode="after")
    def validate_size(self) -> Self:
        # One whole-document ceiling covering text, options, blocks and any property
        # added later. Per-list limits above still bound individual collections.
        size = len(self.model_dump_json(by_alias=True).encode("utf-8"))
        if size > limits.SURVEY_DEFINITION_MAX_BYTES:
            raise ValueError(
                "Survey definition exceeds the maximum allowed size of "
                f"{limits.SURVEY_DEFINITION_MAX_BYTES} bytes (current: {size} bytes)."
            )
        return self
