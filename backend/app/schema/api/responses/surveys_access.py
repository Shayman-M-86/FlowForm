from __future__ import annotations

from datetime import datetime
from typing import cast

from pydantic import BaseModel, ConfigDict, Field

from app.domain.permissions import PERMISSIONS, SurveyPermission
from app.schema.api import limits
from app.schema.orm.core.survey_access import SurveyMembershipRole, SurveyRole


class SurveyRoleResponses(BaseModel):
    """API response shape for a survey role."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    description: str | None
    permissions: list[SurveyPermission] = Field(max_length=limits.SURVEY_ROLE_PERMISSIONS_MAX)
    created_at: datetime

    @classmethod
    def from_orm_with_permissions(cls, role: SurveyRole) -> SurveyRoleResponses:
        allowed_permissions = {*PERMISSIONS.survey.values(), *PERMISSIONS.submission.values()}
        permissions = [
            cast(SurveyPermission, p.name) for p in getattr(role, "permissions", []) if p.name in allowed_permissions
        ]
        return cls.model_construct(
            id=role.id,
            project_id=role.project_id,
            name=role.name,
            description=role.description,
            permissions=permissions,
            created_at=role.created_at,
        )


class SurveyMemberResponses(BaseModel):
    """Embedded user details on a survey member row."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    project_id: int
    role_id: int | None
    status: str


class SurveyMemberRoleResponses(BaseModel):
    """API response shape for a survey membership role assignment."""

    model_config = ConfigDict(from_attributes=True)

    project_id: int
    survey_id: int
    membership_id: int
    role_id: int
    created_at: datetime
    member: SurveyMemberResponses | None = None
    role: SurveyRoleResponses | None = None

    @classmethod
    def from_assignment(cls, smr: SurveyMembershipRole) -> SurveyMemberRoleResponses:
        member_out = (
            SurveyMemberResponses(
                id=smr.membership.id,
                user_id=smr.membership.user_id,
                project_id=smr.membership.project_id,
                role_id=smr.membership.role_id,
                status=smr.membership.status,
            )
            if smr.membership is not None
            else None
        )
        role_out = SurveyRoleResponses.from_orm_with_permissions(smr.role) if smr.role is not None else None
        return cls(
            project_id=smr.project_id,
            survey_id=smr.survey_id,
            membership_id=smr.membership_id,
            role_id=smr.role_id,
            created_at=smr.created_at,
            member=member_out,
            role=role_out,
        )
