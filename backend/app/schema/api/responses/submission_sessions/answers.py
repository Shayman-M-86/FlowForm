"""Saved answer representations using the shared V2 value definitions."""

from typing import Annotated, Literal

from pydantic import Field

from app.schema.models.survey_document.answers import AnsweredAnswer, ClearedAnswer
from app.schema.types import ClientMutationId, SurveyFieldUuid, Timestamp


class SavedAnsweredResponse(AnsweredAnswer):
    """Acknowledged answered state."""

    state: Literal["answered"] = "answered"

    field_uuid: SurveyFieldUuid
    client_mutation_id: ClientMutationId
    saved_at: Timestamp


class SavedClearedResponse(ClearedAnswer):
    """Acknowledged cleared state."""

    state: Literal["cleared"] = "cleared"

    field_uuid: SurveyFieldUuid
    client_mutation_id: ClientMutationId
    saved_at: Timestamp


SubmissionSessionAnswerResponse = Annotated[
    SavedAnsweredResponse | SavedClearedResponse,
    Field(discriminator="state", title="SubmissionSessionAnswerResponse"),
]
