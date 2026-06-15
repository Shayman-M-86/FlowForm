"""Shared Literal enums for the schema layer.

Mirrors the values enforced by DB CHECK constraints. Defined here, below both
the ORM and API schema sub-layers, so each can import these aliases without
crossing sideways into the other (ORM must not import from api/, and api/ must
not import from orm/). These are plain Literal aliases, not Postgres ENUM
types — the DB columns stay TEXT/varchar with CHECK constraints.

When a DB constraint changes, update the matching Literal here so the ORM
mappings, the OpenAPI spec, and any generated TypeScript clients stay accurate.
"""

from __future__ import annotations

from typing import Literal

ProjectMemberStatus = Literal["active", "suspended"]
ProjectInvitationStatus = Literal["pending", "accepted", "declined", "revoked"]
ResponseStoreType = Literal["platform_postgres", "external_postgres"]
SurveyVisibility = Literal["private", "link_only", "public"]
SurveyLinkType = Literal["general", "private", "authenticated"]
SurveyLinkAssignmentSource = Literal["manual", "automated"]
SurveyVersionStatus = Literal["draft", "published", "archived"]
SurveyNodeType = Literal["question", "rule"]
SubjectIdentityType = Literal["email", "authenticated_user"]
SubjectIdentityVerificationStatus = Literal["unverified", "verified"]
SubmissionChannel = Literal["link", "slug", "system"]
SubmissionStatus = Literal["pending", "stored", "failed"]
SubmissionSessionStatus = Literal["in_progress", "completed", "abandoned"]
SubmissionEventType = Literal["session_started", "question_viewed", "answer_saved", "session_completed"]
SubmissionAnswerState = Literal["answered", "cleared"]
ExportFormat = Literal["csv", "json"]

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
RatingStarStyle = Literal["stars"]
RatingStyle = Literal["slider", "emoji", "stars"]

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
