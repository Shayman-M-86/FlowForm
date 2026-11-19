"""Portable admin answer/event projections shared with HTTP responses."""

from pydantic import ConfigDict

from app.schema import limits
from app.schema.enums import SubmissionAnswerState, SubmissionEventType
from app.schema.models.common.base import DataModel
from app.schema.models.survey_document.answer_spec import AnswerSpec
from app.schema.models.survey_document.answer_value import AnswerValue
from app.schema.models.survey_document.fields import SurveyField
from app.schema.types import ReadableId, SurveyFieldUuid, Timestamp


class AnswerSlotResult(DataModel):
    """One document field's encrypted-answer presence and optional plaintext."""

    model_config = ConfigDict(frozen=True, str_max_length=limits.LONG_STRING_MAX)

    field_uuid: SurveyFieldUuid
    field_id: ReadableId | None = None
    has_encrypted_answer: bool
    decrypted: bool
    state: SubmissionAnswerState | None = None
    answer_spec: AnswerSpec | None = None
    answer_value: AnswerValue | None = None
    field: SurveyField | None = None


class SessionEventResult(DataModel):
    """A timeline event, optionally associated with a document field."""

    model_config = ConfigDict(frozen=True)

    event_type: SubmissionEventType
    field_uuid: SurveyFieldUuid | None = None
    received_at: Timestamp
