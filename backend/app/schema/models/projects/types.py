"""Reusable constrained types; enforced when used in Pydantic validation."""

from typing import Annotated
from uuid import UUID

from pydantic import Field, StringConstraints

from app.schema.models.common.types import DatabaseIdentity, TrimmedString

ProjectName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=100,
    ),
]


ProjectId = Annotated[DatabaseIdentity, Field(description="Project identity")]
ProjectRoleId = Annotated[DatabaseIdentity, Field(description="Project role identity")]
ProjectMembershipId = Annotated[DatabaseIdentity, Field(description="Project membership identity")]
ProjectInvitationId = Annotated[DatabaseIdentity, Field(description="Project invitation identity")]
SubjectId = Annotated[UUID, Field(description="Project subject identity")]
SubjectIdentityId = Annotated[UUID, Field(description="Identity attached to a project subject")]
ParticipantId = Annotated[UUID, Field(description="Project participant identity")]


RoleName = Annotated[TrimmedString, Field(max_length=80)]

RoleDescription = Annotated[TrimmedString, Field(max_length=500)]

InvitationMessage = Annotated[TrimmedString, Field(max_length=500)]

SubjectCode = Annotated[TrimmedString, Field(max_length=128)]
