"""Submission-session request contracts and their nested access models."""

from typing import Annotated, Literal

from pydantic import Field

from app.schema.api.common.base import APIRequestModel
from app.schema.models.survey.answers import AnsweredAnswer, ClearedAnswer
from app.schema.types import ClientMutationId, Slug, SurveyAccessToken, SurveyFieldUuid


class PublicSlugAccessNestedModel(APIRequestModel):
    """Start a respondent session using a public survey slug."""

    type: Literal["public_slug"]
    public_slug: Slug


class LinkTokenAccessNestedModel(APIRequestModel):
    """Start a respondent session using a survey access link token."""

    type: Literal["link_token"]
    token: SurveyAccessToken


SessionStartAccessNestedModel = Annotated[
    PublicSlugAccessNestedModel | LinkTokenAccessNestedModel,
    Field(discriminator="type", title="SessionStartAccessNestedModel"),
]


class StartSubmissionSessionRequest(APIRequestModel):
    """Request body for starting or resuming a respondent submission session."""

    access: SessionStartAccessNestedModel


class AnsweredSubmissionRequest(AnsweredAnswer):
    """Save one self-describing field answer."""

    field_uuid: SurveyFieldUuid
    client_mutation_id: ClientMutationId


class ClearedSubmissionRequest(ClearedAnswer):
    """Explicitly clear one field answer."""

    field_uuid: SurveyFieldUuid
    client_mutation_id: ClientMutationId


SaveSubmissionSessionAnswerRequest = Annotated[
    AnsweredSubmissionRequest | ClearedSubmissionRequest,
    Field(discriminator="state", title="SaveSubmissionSessionAnswerRequest"),
]


class SubmissionSessionEventRequest(APIRequestModel):
    """Request body for recording a respondent session event."""

    event_type: Literal["field_viewed"]
    field_uuid: SurveyFieldUuid


class CompleteSubmissionSessionRequest(APIRequestModel):
    """Signal completion without resubmitting answers."""

    action: Literal["complete"]
