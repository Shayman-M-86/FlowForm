from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schema.api.requests.content.rule_schemas import ConditionIn

ScoreNumber = int | float


class MatchingPairIn(BaseModel):
    """Request model for a matching pair in matching answer key scoring.

    Validates that both left and right IDs are non-blank strings.
    """

    model_config = ConfigDict(extra="forbid")

    left_id: str
    right_id: str

    @field_validator("left_id", "right_id")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class NumericRangeScoreIn(BaseModel):
    """Request model for a numeric range with associated score.

    Validates that max is greater than or equal to min.
    """

    model_config = ConfigDict(extra="forbid")

    min: ScoreNumber
    max: ScoreNumber
    score: ScoreNumber

    @model_validator(mode="after")
    def validate_range(self) -> NumericRangeScoreIn:
        if self.max < self.min:
            raise ValueError("max must be greater than or equal to min")
        return self


class ChoiceOptionMapConfig(BaseModel):
    """Configuration for choice option mapping scoring strategy.

    Maps each choice option ID to a score and optionally combines multiple scores
    by summing or taking the maximum value.
    """

    model_config = ConfigDict(extra="forbid")

    option_scores: dict[str, ScoreNumber]
    combine: Literal["sum", "max"] = "sum"

    @field_validator("option_scores")
    @classmethod
    def validate_option_scores(cls, value: dict[str, ScoreNumber]) -> dict[str, ScoreNumber]:
        if not value:
            raise ValueError("option_scores must not be empty")
        if any(not key.strip() for key in value):
            raise ValueError("option_scores keys must not be blank")
        return value


class MatchingAnswerKeyConfig(BaseModel):
    """Configuration for matching answer key scoring strategy.

    Defines correct answer pairs and scoring rules: points awarded for correct
    matches, penalties for incorrect ones, and an optional score ceiling.
    """

    model_config = ConfigDict(extra="forbid")

    correct_pairs: list[MatchingPairIn]
    points_per_correct: ScoreNumber = 1
    penalty_per_incorrect: ScoreNumber = 0
    max_score: ScoreNumber | None = None

    @field_validator("correct_pairs")
    @classmethod
    def validate_correct_pairs(cls, value: list[MatchingPairIn]) -> list[MatchingPairIn]:
        if not value:
            raise ValueError("correct_pairs must not be empty")
        return value

    @model_validator(mode="after")
    def validate_max_score(self) -> MatchingAnswerKeyConfig:
        if self.max_score is not None and self.max_score < 0:
            raise ValueError("max_score must be greater than or equal to 0")
        return self


class RatingDirectConfig(BaseModel):
    """Configuration for direct rating scoring strategy.

    Multiplies the raw rating value by the specified multiplier.
    """

    model_config = ConfigDict(extra="forbid")

    multiplier: ScoreNumber = 1


class FieldNumericRangesConfig(BaseModel):
    """Configuration for field numeric ranges scoring strategy.

    Defines numeric ranges and their corresponding scores for evaluating numeric
    field answers.
    """

    model_config = ConfigDict(extra="forbid")

    ranges: list[NumericRangeScoreIn]

    @field_validator("ranges")
    @classmethod
    def validate_ranges_not_empty(
        cls,
        value: list[NumericRangeScoreIn],
    ) -> list[NumericRangeScoreIn]:
        if not value:
            raise ValueError("ranges must not be empty")
        return value


class ChoiceOptionMapScoringSchemaIn(BaseModel):
    """Request schema for choice option mapping scoring rule.

    Applies scores based on selected choice options, targeting a specific bucket
    and optionally filtered by a condition.
    """

    model_config = ConfigDict(extra="forbid")

    target: str
    bucket: str
    condition: ConditionIn | None = None
    strategy: Literal["choice_option_map"]
    config: ChoiceOptionMapConfig

    @field_validator("target", "bucket")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class MatchingAnswerKeyScoringSchemaIn(BaseModel):
    """Request schema for matching answer key scoring rule.

    Evaluates matching answers against correct pairs, scoring based on accuracy.
    Targets a specific bucket and optionally filtered by a condition.
    """

    model_config = ConfigDict(extra="forbid")

    target: str
    bucket: str
    condition: ConditionIn | None = None
    strategy: Literal["matching_answer_key"]
    config: MatchingAnswerKeyConfig

    @field_validator("target", "bucket")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class RatingDirectScoringSchemaIn(BaseModel):
    """Request schema for direct rating scoring rule.

    Directly scores a rating response by multiplying by a factor, targeting a
    specific bucket and optionally filtered by a condition.
    """

    model_config = ConfigDict(extra="forbid")

    target: str
    bucket: str
    condition: ConditionIn | None = None
    strategy: Literal["rating_direct"]
    config: RatingDirectConfig

    @field_validator("target", "bucket")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class FieldNumericRangesScoringSchemaIn(BaseModel):
    """Request schema for field numeric ranges scoring rule.

    Scores numeric responses based on which range interval they fall into,
    targeting a specific bucket and optionally filtered by a condition.
    """

    model_config = ConfigDict(extra="forbid")

    target: str
    bucket: str
    condition: ConditionIn | None = None
    strategy: Literal["field_numeric_ranges"]
    config: FieldNumericRangesConfig

    @field_validator("target", "bucket")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


ScoringRuleSchemaIn = Annotated[
    ChoiceOptionMapScoringSchemaIn
    | MatchingAnswerKeyScoringSchemaIn
    | RatingDirectScoringSchemaIn
    | FieldNumericRangesScoringSchemaIn,
    Field(discriminator="strategy"),
]
"""Union type for all scoring rule request schemas.

Discriminated by the 'strategy' field to route to the appropriate schema.
"""
