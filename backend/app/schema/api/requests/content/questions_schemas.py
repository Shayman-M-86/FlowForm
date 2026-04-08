from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ChoiceOptionIn(BaseModel):
    """Represents a single selectable option for a choice question."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str

    @field_validator("id", "label")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class MatchingItemIn(BaseModel):
    """Represents one item on either side of a matching question."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str

    @field_validator("id", "label")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class ChoiceQuestionConfig(BaseModel):
    """Defines selection constraints and options for a choice question."""

    model_config = ConfigDict(extra="forbid")

    options: list[ChoiceOptionIn]
    min_selected: int = Field(ge=0)
    max_selected: int = Field(ge=1)

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
    def validate_selection_bounds(self) -> ChoiceQuestionConfig:
        if self.max_selected < self.min_selected:
            raise ValueError("max_selected must be greater than or equal to min_selected")

        if self.max_selected > len(self.options):
            raise ValueError("max_selected cannot be greater than the number of options")

        return self


class FieldQuestionConfig(BaseModel):
    """Defines the input type for a field-based question."""

    model_config = ConfigDict(extra="forbid")

    field_type: Literal["text", "email", "number", "date", "phone"]


class MatchingQuestionConfig(BaseModel):
    """Defines the left and right item sets for a matching question."""

    model_config = ConfigDict(extra="forbid")

    left_items: list[MatchingItemIn]
    right_items: list[MatchingItemIn]

    @field_validator("left_items", "right_items")
    @classmethod
    def validate_items_not_empty(cls, value: list[MatchingItemIn]) -> list[MatchingItemIn]:
        if not value:
            raise ValueError("must contain at least one item")
        return value

    @model_validator(mode="after")
    def validate_unique_ids(self) -> MatchingQuestionConfig:
        left_ids = [item.id for item in self.left_items]
        right_ids = [item.id for item in self.right_items]

        if len(left_ids) != len(set(left_ids)):
            raise ValueError("left_items ids must be unique")

        if len(right_ids) != len(set(right_ids)):
            raise ValueError("right_items ids must be unique")

        return self


class RatingQuestionConfig(BaseModel):
    """Defines the minimum and maximum bounds for a rating question."""

    model_config = ConfigDict(extra="forbid")

    min: int | float
    max: int | float

    @model_validator(mode="after")
    def validate_range(self) -> RatingQuestionConfig:
        if self.max <= self.min:
            raise ValueError("max must be greater than min")
        return self


class ChoiceQuestionSchemaIn(BaseModel):
    """Accepts an incoming choice-question schema payload."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    family: Literal["choice"]
    label: str
    schema_: ChoiceQuestionConfig = Field(
        validation_alias="schema",
        serialization_alias="schema",
    )
    ui: dict[str, Any] = Field(default_factory=dict)

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("label must not be blank")
        return value


class FieldQuestionSchemaIn(BaseModel):
    """Accepts an incoming field-question schema payload."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    family: Literal["field"]
    label: str
    schema_: FieldQuestionConfig = Field(
        validation_alias="schema",
        serialization_alias="schema",
    )
    ui: dict[str, Any] = Field(default_factory=dict)

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("label must not be blank")
        return value


class MatchingQuestionSchemaIn(BaseModel):
    """Accepts an incoming matching-question schema payload."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    family: Literal["matching"]
    label: str
    schema_: MatchingQuestionConfig = Field(
        validation_alias="schema",
        serialization_alias="schema",
    )
    ui: dict[str, Any] = Field(default_factory=dict)

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("label must not be blank")
        return value


class RatingQuestionSchemaIn(BaseModel):
    """Accepts an incoming rating-question schema payload."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    family: Literal["rating"]
    label: str
    schema_: RatingQuestionConfig = Field(
        validation_alias="schema",
        serialization_alias="schema",
    )
    ui: dict[str, Any] = Field(default_factory=dict)

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


class CreateQuestionRequest(BaseModel):
    """Validates requests that create a new question schema entry."""

    model_config = ConfigDict(extra="forbid")

    question_key: str
    question_schema: QuestionSchemaIn

    @field_validator("question_key")
    @classmethod
    def validate_question_key(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question_key must not be blank")
        return value


class UpdateQuestionRequest(BaseModel):
    """Validates partial updates to an existing question schema entry."""

    model_config = ConfigDict(extra="forbid")

    question_key: str | None = None
    question_schema: QuestionSchemaIn | None = None

    @field_validator("question_key")
    @classmethod
    def validate_question_key(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("question_key must not be blank")
        return value
