from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from app.schema.api.submission_sessions.answer_payload import (
    ChoiceAnswerValue,
    DateFieldAnswerValue,
    EmailFieldAnswerValue,
    EmojiRatingAnswerValue,
    LongTextFieldAnswerValue,
    MatchingAnswerValue,
    NumberFieldAnswerValue,
    PhoneFieldAnswerValue,
    ShortTextFieldAnswerValue,
    SliderRatingAnswerValue,
    StarsRatingAnswerValue,
    SubmissionAnswerValue,
)
from app.schema.enums import AnswerFamily, SubmissionAnswerState


class SaveSubmissionSessionAnswerRequest(BaseModel):
    """Request body for saving or clearing one respondent answer revision."""

    model_config = ConfigDict(extra="forbid")

    client_mutation_id: UUID
    state: SubmissionAnswerState
    answer_family: AnswerFamily | None = None
    answer_value: SubmissionAnswerValue | None = None

    @model_validator(mode="after")
    def validate_answer_state(self) -> SaveSubmissionSessionAnswerRequest:
        if self.state == "answered":
            if self.answer_family is None:
                raise ValueError("answer_family is required when state is 'answered'.")
            if self.answer_value is None:
                raise ValueError("answer_value is required when state is 'answered'.")
            self._validate_answer_value_matches_family()
            return self

        if self.answer_family is not None:
            raise ValueError("answer_family must be omitted when state is 'cleared'.")
        if self.answer_value is not None:
            raise ValueError("answer_value must be omitted when state is 'cleared'.")
        return self

    def _validate_answer_value_matches_family(self) -> None:
        if self.answer_family == "choice" and not isinstance(self.answer_value, ChoiceAnswerValue):
            raise ValueError("answer_value must be a choice answer when answer_family is 'choice'.")
        if self.answer_family == "field" and not isinstance(
            self.answer_value,
            (
                ShortTextFieldAnswerValue,
                LongTextFieldAnswerValue,
                EmailFieldAnswerValue,
                NumberFieldAnswerValue,
                DateFieldAnswerValue,
                PhoneFieldAnswerValue,
            ),
        ):
            raise ValueError("answer_value must be a field answer when answer_family is 'field'.")
        if self.answer_family == "matching" and not isinstance(self.answer_value, MatchingAnswerValue):
            raise ValueError("answer_value must be a matching answer when answer_family is 'matching'.")
        if self.answer_family == "rating" and not isinstance(
            self.answer_value,
            (
                SliderRatingAnswerValue,
                StarsRatingAnswerValue,
                EmojiRatingAnswerValue,
            ),
        ):
            raise ValueError("answer_value must be a rating answer when answer_family is 'rating'.")
