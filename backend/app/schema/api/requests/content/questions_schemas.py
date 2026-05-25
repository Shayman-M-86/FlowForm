from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schema.api import limits
from app.schema.api.enums import (
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

SchemaIdStr = Annotated[str, Field(max_length=limits.SCHEMA_ID_MAX)]


class ChoiceOptionIn(BaseModel):
    """Represents a single selectable option for a choice question."""

    model_config = ConfigDict(extra="forbid")

    id: SchemaIdStr
    label: str = Field(max_length=limits.CHOICE_OPTION_LABEL_MAX)

    @field_validator("id", "label")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class MatchingItemIn(BaseModel):
    """Represents one item on either side of a matching question."""

    model_config = ConfigDict(extra="forbid")

    id: SchemaIdStr
    label: str = Field(max_length=limits.MATCHING_ITEM_LABEL_MAX)

    @field_validator("id", "label")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class RangeIn(BaseModel):
    """Defines min and max bounds for a rating question."""

    model_config = ConfigDict(extra="forbid")

    min: int | float = Field(ge=limits.RATING_RANGE_MIN, le=limits.RATING_RANGE_MAX)
    max: int | float = Field(ge=limits.RATING_RANGE_MIN, le=limits.RATING_RANGE_MAX)

    @model_validator(mode="after")
    def validate_range(self):
        if self.max <= self.min:
            raise ValueError("max must be greater than min")
        return self


class ChoiceQuestionConfig(BaseModel):
    """Defines selection constraints and options for a choice question."""

    model_config = ConfigDict(extra="forbid")

    options: list[ChoiceOptionIn] = Field(max_length=limits.QUESTION_ITEMS_MAX)
    min_selected: int = Field(ge=limits.CHOICE_MIN_SELECTED_MIN)
    max_selected: int = Field(ge=limits.CHOICE_MAX_SELECTED_MIN)

    @field_validator("options")
    @classmethod
    def validate_options(cls, value: list[ChoiceOptionIn]) -> list[ChoiceOptionIn]:
        if not value:
            raise ValueError("options must contain at least one item")

        if len(value) > limits.QUESTION_ITEMS_MAX:
            raise ValueError(f"options cannot contain more than {limits.QUESTION_ITEMS_MAX} items")

        ids = [item.id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("option ids must be unique")

        return value

    @model_validator(mode="after")
    def validate_selection_bounds(self) -> ChoiceQuestionConfig:
        if self.max_selected < self.min_selected:
            raise ValueError("max_selected must be greater than or equal to min_selected")

        if self.max_selected > len(self.options):
            raise ValueError("max_selected cannot be greater than the number of options")

        return self

    @model_validator(mode="after")
    def validate_total_option_characters(self) -> ChoiceQuestionConfig:
        total_chars = sum(len(option.label) for option in self.options)

        if total_chars > limits.CHOICE_OPTION_LABELS_TOTAL_MAX:
            raise ValueError(
                "total characters across all option labels cannot exceed "
                f"{limits.CHOICE_OPTION_LABELS_TOTAL_MAX} (current: {total_chars})"
            )

        return self


class FieldQuestionConfig(BaseModel):
    """Defines the input type for a field-based question."""

    model_config = ConfigDict(extra="forbid")

    field_type: FieldQuestionType


class MatchingQuestionConfig(BaseModel):
    """Defines the prompt and match item sets for a matching question."""

    model_config = ConfigDict(extra="forbid")

    prompts: list[MatchingItemIn] = Field(max_length=limits.QUESTION_ITEMS_MAX)
    matches: list[MatchingItemIn] = Field(max_length=limits.QUESTION_ITEMS_MAX)

    @field_validator("prompts", "matches")
    @classmethod
    def validate_items_not_empty(cls, value: list[MatchingItemIn]) -> list[MatchingItemIn]:
        if not value:
            raise ValueError("must contain at least one item")

        if len(value) > limits.QUESTION_ITEMS_MAX:
            raise ValueError(f"cannot contain more than {limits.QUESTION_ITEMS_MAX} items")

        return value

    @model_validator(mode="after")
    def validate_unique_ids(self) -> MatchingQuestionConfig:
        prompt_ids = [item.id for item in self.prompts]
        match_ids = [item.id for item in self.matches]

        if len(prompt_ids) != len(set(prompt_ids)):
            raise ValueError("prompt ids must be unique")

        if len(match_ids) != len(set(match_ids)):
            raise ValueError("match ids must be unique")

        return self

    @model_validator(mode="after")
    def validate_total_characters(self) -> MatchingQuestionConfig:
        total_chars = sum(len(item.label) for item in self.prompts) + sum(len(item.label) for item in self.matches)

        if total_chars > limits.MATCHING_ITEMS_TOTAL_LABEL_MAX:
            raise ValueError(
                "total characters across prompts and matches cannot exceed "
                f"{limits.MATCHING_ITEMS_TOTAL_LABEL_MAX} (current: {total_chars})"
            )

        return self


class RatingUIIn(BaseModel):
    """Base UI for all rating questions — includes left/right labels."""

    model_config = ConfigDict(extra="forbid")

    left_label: str = Field(max_length=limits.RATING_LABEL_MAX)
    right_label: str = Field(max_length=limits.RATING_LABEL_MAX)

    @field_validator("left_label", "right_label")
    @classmethod
    def validate_labels_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("label must not be blank")
        return value


class RatingSliderSchemaIn(BaseModel):
    """Schema for slider-style rating questions."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    range: RangeIn
    step: int | float = Field(gt=limits.RATING_STEP_MIN_EXCLUSIVE)

    @model_validator(mode="after")
    def validate_step_divides_range(self):
        range_diff = self.range.max - self.range.min
        # Check if step divides evenly into the range difference
        if range_diff % self.step != 0:
            raise ValueError(
                f"step must be a divisor of the range difference ({range_diff}); {self.step} does not divide evenly"
            )
        return self


class RatingEmojiSchemaIn(BaseModel):
    """Schema for emoji-style rating questions."""

    model_config = ConfigDict(extra="forbid")

    emoji_list: RatingEmojiList
    words: bool = False


class RatingStarSchemaIn(BaseModel):
    """Schema for star-style rating questions."""

    model_config = ConfigDict(extra="forbid")

    stars: int = Field(ge=limits.RATING_STARS_MIN, le=limits.RATING_STARS_MAX)


# ============================================================================
# NESTED INPUT MODELS (what clients send)
# ============================================================================


class ChoiceQuestionNestedIn(BaseModel):
    """Input for a choice question with nested schema/ui."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: ChoiceQuestionConfig = Field(
        validation_alias="schema",
        serialization_alias="schema",
    )
    ui: dict[str, Any] = Field(default_factory=dict)


class FieldQuestionUIIn(BaseModel):
    """Validates field question UI configuration."""

    model_config = ConfigDict(extra="forbid")

    placeholder: str = Field(max_length=limits.FIELD_PLACEHOLDER_MAX, default="")

    @field_validator("placeholder")
    @classmethod
    def validate_placeholder_not_required_blank(cls, value: str) -> str:
        # Allow empty string, but if provided, it can't be just whitespace
        if value and not value.strip():
            raise ValueError("placeholder must not be blank")
        return value


class FieldQuestionNestedIn(BaseModel):
    """Input for a field question with nested schema/ui."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: FieldQuestionConfig = Field(
        validation_alias="schema",
        serialization_alias="schema",
    )
    ui: FieldQuestionUIIn = Field(default_factory=FieldQuestionUIIn)


class MatchingQuestionNestedIn(BaseModel):
    """Input for a matching question with nested schema/ui."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: MatchingQuestionConfig = Field(
        validation_alias="schema",
        serialization_alias="schema",
    )
    ui: dict[str, Any] = Field(default_factory=dict)


class RatingSliderNestedIn(BaseModel):
    """Input for a slider-style rating question."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    style: RatingSliderStyle
    schema_: RatingSliderSchemaIn = Field(
        validation_alias="schema",
        serialization_alias="schema",
    )
    ui: RatingUIIn


class RatingEmojiNestedIn(BaseModel):
    """Input for an emoji-style rating question."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    style: RatingEmojiStyle
    schema_: RatingEmojiSchemaIn = Field(
        validation_alias="schema",
        serialization_alias="schema",
    )
    ui: RatingUIIn


class RatingStarNestedIn(BaseModel):
    """Input for a star-style rating question."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    style: RatingStarStyle
    schema_: RatingStarSchemaIn = Field(
        validation_alias="schema",
        serialization_alias="schema",
    )
    ui: RatingUIIn


RatingQuestionNestedIn = Annotated[
    RatingSliderNestedIn | RatingEmojiNestedIn | RatingStarNestedIn,
    Field(discriminator="style"),
]


# ============================================================================
# TOP-LEVEL NESTED QUESTION INPUTS
# ============================================================================


class ChoiceQuestionSchemaIn(BaseModel):
    """Accepts an incoming choice-question schema payload (nested structure)."""

    model_config = ConfigDict(extra="forbid")

    id: SchemaIdStr
    family: ChoiceFamily
    label: str = Field(max_length=limits.QUESTION_LABEL_MAX)
    title: str | None = Field(default=None, max_length=limits.QUESTION_TITLE_MAX)
    choice: ChoiceQuestionNestedIn

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("id must not be blank")
        return value

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("label must not be blank")
        return value


class FieldQuestionSchemaIn(BaseModel):
    """Accepts an incoming field-question schema payload (nested structure)."""

    model_config = ConfigDict(extra="forbid")

    id: SchemaIdStr
    family: FieldFamily
    label: str = Field(max_length=limits.QUESTION_LABEL_MAX)
    title: str | None = Field(default=None, max_length=limits.QUESTION_TITLE_MAX)
    field: FieldQuestionNestedIn

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("id must not be blank")
        return value

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("label must not be blank")
        return value


class MatchingQuestionSchemaIn(BaseModel):
    """Accepts an incoming matching-question schema payload (nested structure)."""

    model_config = ConfigDict(extra="forbid")

    id: SchemaIdStr
    family: MatchingFamily
    label: str = Field(max_length=limits.QUESTION_LABEL_MAX)
    title: str | None = Field(default=None, max_length=limits.QUESTION_TITLE_MAX)
    matching: MatchingQuestionNestedIn

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("id must not be blank")
        return value

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("label must not be blank")
        return value


class RatingQuestionSchemaIn(BaseModel):
    """Accepts an incoming rating-question schema payload (nested structure)."""

    model_config = ConfigDict(extra="forbid")

    id: SchemaIdStr
    family: RatingFamily
    label: str = Field(max_length=limits.QUESTION_LABEL_MAX)
    title: str | None = Field(default=None, max_length=limits.QUESTION_TITLE_MAX)
    rating: RatingQuestionNestedIn

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("id must not be blank")
        return value

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("label must not be blank")
        return value


QuestionSchemaIn = Annotated[
    ChoiceQuestionSchemaIn | FieldQuestionSchemaIn | MatchingQuestionSchemaIn | RatingQuestionSchemaIn,
    Field(discriminator="family"),
]
