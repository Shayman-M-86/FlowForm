"""Shared Literal enums for API request/response schemas.

Mirrors the values enforced by DB CHECK constraints. Defined here (not in
the ORM layer) because the schema layer must not import from models per
the project layer rules.

When the DB constraint changes, update the matching Literal here so the
OpenAPI spec and any generated TypeScript clients stay accurate.
"""

from __future__ import annotations

from typing import Literal

ProjectMemberStatus = Literal["active", "suspended"]
ProjectInvitationStatus = Literal["pending", "accepted", "declined", "revoked"]
SurveyVisibility = Literal["private", "link_only", "public"]
SurveyVersionStatus = Literal["draft", "published", "archived"]
SurveyNodeType = Literal["question", "rule"]
SubmissionChannel = Literal["link", "slug", "system"]
SubmissionStatus = Literal["pending", "stored", "failed"]

ChoiceFamily = Literal["choice"]
FieldFamily = Literal["field"]
MatchingFamily = Literal["matching"]
RatingFamily = Literal["rating"]
QuestionFamily = Literal["choice", "field", "matching", "rating"]
AnswerFamily = Literal["choice", "field", "matching", "rating"]

FieldQuestionType = Literal["short_text", "long_text", "email", "number", "date", "phone"]
RatingEmojiList = Literal["sad_to_happy", "angry_to_happy", "disgust_to_happy"]
RatingSliderStyle = Literal["slider"]
RatingEmojiStyle = Literal["emoji"]
RatingStarStyle = Literal["star"]
RatingStyle = Literal["slider", "emoji", "star"]

NumberFieldType = Literal["number"]
DateFieldType = Literal["date"]
NumericFieldOperator = Literal["LT", "LTE", "GT", "GTE", "EQ", "NEQ"]
DateFieldOperator = Literal["before", "after"]
FieldOperator = Literal["LT", "LTE", "GT", "GTE", "EQ", "NEQ", "before", "after"]
IfMatch = Literal["ALL", "ANY", "NONE"]
SkipAction = Literal["skip_to", "end_and_submit", "end_and_discard"]

ScoringCombine = Literal["sum", "max"]
ChoiceOptionMapStrategy = Literal["choice_option_map"]
MatchingAnswerKeyStrategy = Literal["matching_answer_key"]
RatingDirectStrategy = Literal["rating_direct"]
FieldNumericRangesStrategy = Literal["field_numeric_ranges"]
ScoringStrategy = Literal["choice_option_map", "matching_answer_key", "rating_direct", "field_numeric_ranges"]
