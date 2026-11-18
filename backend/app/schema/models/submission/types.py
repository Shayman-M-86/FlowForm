"""Submission identifiers shared by requests, responses and persistence."""

from typing import Annotated
from uuid import UUID

from pydantic import Field

ClientMutationId = Annotated[UUID, Field(description="Identity of a client answer mutation")]
SubmissionSessionId = Annotated[UUID, Field(description="Respondent submission session identity")]
type AnswerList[T] = Annotated[list[T], Field(description="Saved answers belonging to the session")]
