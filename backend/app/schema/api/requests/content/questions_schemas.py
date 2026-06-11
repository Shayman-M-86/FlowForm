from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schema.api import limits
from app.schema.api.requests.field_types import (
    ChoiceOptionLabel,
    MatchingItemLabel,
    QuestionLabel,
    QuestionTitle,
    RatingLabel,
    SchemaIdStr,
)
from app.schema.enums import (
    ChoiceFamily,
    FieldFamily,
    FieldQuestionType,
    MatchingFamily,
    RatingEmojiList,
    RatingEmojiStyle,
    RatingFamily,
    RatingSliderStyle,
    RatingStarStyle,
)

# ── Shared leaf models ────────────────────────────────────────────────────────


class ChoiceOptionIn(BaseModel):
    """A single selectable option for a choice question."""

    model_config = ConfigDict(extra="forbid")

    id: SchemaIdStr
    label: ChoiceOptionLabel


class MatchingItemIn(BaseModel):
    """One item on either side of a matching question."""

    model_config = ConfigDict(extra="forbid")

    id: SchemaIdStr
    label: MatchingItemLabel


class RatingUIIn(BaseModel):
    """Left/right labels for all rating variants."""

    model_config = ConfigDict(extra="forbid")

    left_label: RatingLabel
    right_label: RatingLabel


# ── Choice definition ─────────────────────────────────────────────────────────


class ChoiceDefinitionIn(BaseModel):
    """definition block for a choice question."""

    model_config = ConfigDict(extra="forbid")

    min: int = Field(ge=limits.CHOICE_MIN_SELECTED_MIN)
    max: int = Field(ge=limits.CHOICE_MAX_SELECTED_MIN)
    options: list[ChoiceOptionIn] = Field(max_length=limits.QUESTION_ITEMS_MAX)

    @field_validator("options")
    @classmethod
    def validate_options(cls, value: list[ChoiceOptionIn]) -> list[ChoiceOptionIn]:
        if not value:
            raise ValueError("options must contain at least one item")
        ids = [item.id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("option ids must be unique")
        return value

    @model_validator(mode="after")
    def validate_selection_bounds(self) -> ChoiceDefinitionIn:
        if self.max < self.min:
            raise ValueError("max must be greater than or equal to min")
        if self.max > len(self.options):
            raise ValueError("max cannot be greater than the number of options")
        return self

    @model_validator(mode="after")
    def validate_total_option_characters(self) -> ChoiceDefinitionIn:
        total_chars = sum(len(option.label) for option in self.options)
        if total_chars > limits.CHOICE_OPTION_LABELS_TOTAL_MAX:
            raise ValueError(
                "total characters across all option labels cannot exceed "
                f"{limits.CHOICE_OPTION_LABELS_TOTAL_MAX} (current: {total_chars})"
            )
        return self


# ── Field definition ──────────────────────────────────────────────────────────


class FieldUIIn(BaseModel):
    """UI block for a field question."""

    model_config = ConfigDict(extra="forbid")

    placeholder: str = Field(default="", max_length=limits.FIELD_PLACEHOLDER_MAX)

    @field_validator("placeholder")
    @classmethod
    def validate_placeholder(cls, value: str) -> str:
        if value and not value.strip():
            raise ValueError("placeholder must not be blank")
        return value


class FieldDefinitionIn(BaseModel):
    """definition block for a field question."""

    model_config = ConfigDict(extra="forbid")

    field_type: FieldQuestionType
    ui: FieldUIIn = Field(default_factory=FieldUIIn)


# ── Matching definition ───────────────────────────────────────────────────────


class MatchingDefinitionIn(BaseModel):
    """definition block for a matching question."""

    model_config = ConfigDict(extra="forbid")

    prompts: list[MatchingItemIn] = Field(max_length=limits.QUESTION_ITEMS_MAX)
    matches: list[MatchingItemIn] = Field(max_length=limits.QUESTION_ITEMS_MAX)

    @field_validator("prompts", "matches")
    @classmethod
    def validate_items_not_empty(cls, value: list[MatchingItemIn]) -> list[MatchingItemIn]:
        if not value:
            raise ValueError("must contain at least one item")
        return value

    @model_validator(mode="after")
    def validate_unique_ids(self) -> MatchingDefinitionIn:
        prompt_ids = [item.id for item in self.prompts]
        match_ids = [item.id for item in self.matches]
        if len(prompt_ids) != len(set(prompt_ids)):
            raise ValueError("prompt ids must be unique")
        if len(match_ids) != len(set(match_ids)):
            raise ValueError("match ids must be unique")
        return self

    @model_validator(mode="after")
    def validate_total_characters(self) -> MatchingDefinitionIn:
        total_chars = sum(len(i.label) for i in self.prompts) + sum(len(i.label) for i in self.matches)
        if total_chars > limits.MATCHING_ITEMS_TOTAL_LABEL_MAX:
            raise ValueError(
                "total characters across prompts and matches cannot exceed "
                f"{limits.MATCHING_ITEMS_TOTAL_LABEL_MAX} (current: {total_chars})"
            )
        return self


# ── Rating definitions (discriminated by variant) ────────────────────────────


class RatingRangeIn(BaseModel):
    """Range block for a slider rating — min, max, and step in one object."""

    model_config = ConfigDict(extra="forbid")

    min: int | float = Field(ge=limits.RATING_RANGE_MIN, le=limits.RATING_RANGE_MAX)
    max: int | float = Field(ge=limits.RATING_RANGE_MIN, le=limits.RATING_RANGE_MAX)
    step: int | float = Field(gt=limits.RATING_STEP_MIN_EXCLUSIVE)

    @model_validator(mode="after")
    def validate_range_and_step(self) -> RatingRangeIn:
        if self.max <= self.min:
            raise ValueError("max must be greater than min")
        range_diff = self.max - self.min
        if range_diff % self.step != 0:
            raise ValueError(
                f"step must be a divisor of the range difference ({range_diff})"
            )
        return self


class RatingSliderDefinitionIn(BaseModel):
    """definition block for a slider-style rating question."""

    model_config = ConfigDict(extra="forbid")

    variant: RatingSliderStyle
    range: RatingRangeIn
    ui: RatingUIIn


class RatingStarDefinitionIn(BaseModel):
    """definition block for a star-style rating question."""

    model_config = ConfigDict(extra="forbid")

    variant: RatingStarStyle
    stars: int = Field(ge=limits.RATING_STARS_MIN, le=limits.RATING_STARS_MAX)
    ui: RatingUIIn


class RatingEmojiDefinitionIn(BaseModel):
    """definition block for an emoji-style rating question."""

    model_config = ConfigDict(extra="forbid")

    variant: RatingEmojiStyle
    emoji_list: RatingEmojiList
    words: bool = False
    ui: RatingUIIn


RatingDefinitionIn = Annotated[
    RatingSliderDefinitionIn | RatingStarDefinitionIn | RatingEmojiDefinitionIn,
    Field(discriminator="variant"),
]


# ── Top-level question content schemas ───────────────────────────────────────


class ChoiceQuestionSchemaIn(BaseModel):
    """Incoming choice-question content schema."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"x-flowform-export": "builder"})

    family: ChoiceFamily
    label: QuestionLabel
    title: QuestionTitle | None = None
    definition: ChoiceDefinitionIn


class FieldQuestionSchemaIn(BaseModel):
    """Incoming field-question content schema."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"x-flowform-export": "builder"})

    family: FieldFamily
    label: QuestionLabel
    title: QuestionTitle | None = None
    definition: FieldDefinitionIn


class MatchingQuestionSchemaIn(BaseModel):
    """Incoming matching-question content schema."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"x-flowform-export": "builder"})

    family: MatchingFamily
    label: QuestionLabel
    title: QuestionTitle | None = None
    definition: MatchingDefinitionIn


class RatingQuestionSchemaIn(BaseModel):
    """Incoming rating-question content schema."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"x-flowform-export": "builder"})

    family: RatingFamily
    label: QuestionLabel
    title: QuestionTitle | None = None
    definition: RatingDefinitionIn


QuestionSchemaIn = Annotated[
    ChoiceQuestionSchemaIn | FieldQuestionSchemaIn | MatchingQuestionSchemaIn | RatingQuestionSchemaIn,
    Field(discriminator="family"),
]
