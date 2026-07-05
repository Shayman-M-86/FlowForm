"""Question metadata mapping for admin results.

Pure helpers: no DB session, no crypto. They translate persisted question
content into the small (question_key, answer_family) pairs the result tree needs,
and validate decrypted raw values into canonical answer models when possible.
"""

from __future__ import annotations

import logging
from typing import Any, cast, get_args
from uuid import UUID

from pydantic import ValidationError

from app.schema.api.submission_sessions.answer_payload import (
    SubmissionAnswerValue,
    parse_answer_value,
)
from app.schema.enums import AnswerFamily, QuestionFamily, SubmissionAnswerState
from app.schema.orm.core.survey_content import SurveyQuestion

logger = logging.getLogger(__name__)

_QUESTION_FAMILIES: frozenset[str] = frozenset(get_args(QuestionFamily))

QuestionMetaMap = dict[UUID, tuple[str | None, AnswerFamily | None]]


def build_question_meta_map(question_nodes: list[SurveyQuestion]) -> QuestionMetaMap:
    """Map each question node id to its question key and answer family."""
    return {q.id: (q.question_key, answer_family_from_schema(q.question_schema)) for q in question_nodes}


def answer_family_from_schema(question_schema: object) -> AnswerFamily | None:
    """Read the top-level family discriminator from persisted question content."""
    if not isinstance(question_schema, dict):
        return None
    raw_family = question_schema.get("family")
    if raw_family not in _QUESTION_FAMILIES:
        return None
    return cast(AnswerFamily, raw_family)


def resolve_answer_value(
    *,
    answer_family: AnswerFamily | None,
    answer_state: SubmissionAnswerState,
    raw_value: Any,
) -> SubmissionAnswerValue | dict[str, Any] | None:
    """Validate decrypted raw values into canonical answer models when possible."""
    if raw_value is None or answer_state == "cleared" or answer_family is None:
        return raw_value
    if not isinstance(raw_value, dict):
        return raw_value
    try:
        return parse_answer_value(answer_family, raw_value)
    except ValidationError:
        logger.warning(
            "Decrypted answer value did not match canonical %s shape; keeping raw value.",
            answer_family,
        )
        return raw_value
