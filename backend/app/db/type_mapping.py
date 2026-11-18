"""SQL storage for shared nominal identities; validation remains in Pydantic."""

from sqlalchemy import BigInteger, Text
from sqlalchemy.dialects.postgresql import UUID

from app.schema.types import (
    Auth0UserId,
    ChoiceOptionUuid,
    ClientMutationId,
    MatchingMatchUuid,
    MatchingPromptUuid,
    ParticipantId,
    ProjectId,
    ProjectInvitationId,
    ProjectMembershipId,
    ProjectRoleId,
    ResponseStoreId,
    SubjectId,
    SubjectIdentityId,
    SubmissionSessionId,
    SurveyFieldUuid,
    SurveyId,
    SurveyLinkId,
    SurveyRoleId,
    SurveyVersionId,
    UserId,
)

IDENTITY_TYPE_MAP = {
    UserId: BigInteger,
    Auth0UserId: Text,
    ProjectId: BigInteger,
    ProjectRoleId: BigInteger,
    ProjectMembershipId: BigInteger,
    ProjectInvitationId: BigInteger,
    SubjectId: UUID(as_uuid=True),
    SubjectIdentityId: UUID(as_uuid=True),
    ParticipantId: UUID(as_uuid=True),
    SurveyVersionId: BigInteger,
    SurveyId: BigInteger,
    SurveyRoleId: BigInteger,
    SurveyLinkId: UUID(as_uuid=True),
    SurveyFieldUuid: UUID(as_uuid=True),
    ChoiceOptionUuid: UUID(as_uuid=True),
    MatchingPromptUuid: UUID(as_uuid=True),
    MatchingMatchUuid: UUID(as_uuid=True),
    ClientMutationId: UUID(as_uuid=True),
    SubmissionSessionId: UUID(as_uuid=True),
    ResponseStoreId: BigInteger,
}
