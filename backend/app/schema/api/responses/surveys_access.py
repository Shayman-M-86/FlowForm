from __future__ import annotations

from typing import cast

from pydantic import ConfigDict

from app.domain.permissions import PERMISSIONS
from app.schema.api.common.base import APIResponseModel
from app.schema.api.common.types import SurveyPermission, SurveyPermissionSet
from app.schema.enums import ProjectMemberStatus
from app.schema.models.common.types import Timestamp
from app.schema.models.identity.types import UserId
from app.schema.models.projects.types import ProjectId, ProjectMembershipId, ProjectRoleId, RoleDescription, RoleName
from app.schema.models.survey.types import SurveyId, SurveyRoleId
from app.schema.orm.core.survey_access import SurveyMembershipRole, SurveyRole


class SurveyRoleResponses(APIResponseModel):
    """API response shape for a survey role."""

    model_config = ConfigDict(from_attributes=True)

    id: SurveyRoleId
    project_id: ProjectId
    name: RoleName
    description: RoleDescription | None
    permissions: SurveyPermissionSet
    created_at: Timestamp

    @classmethod
    def from_orm_with_permissions(cls, role: SurveyRole) -> SurveyRoleResponses:
        allowed_permissions = {*PERMISSIONS.survey.values(), *PERMISSIONS.submission.values()}
        permissions = {
            cast(SurveyPermission, p.name) for p in getattr(role, "permissions", []) if p.name in allowed_permissions
        }
        return cls.model_construct(
            id=role.id,
            project_id=role.project_id,
            name=role.name,
            description=role.description,
            permissions=permissions,
            created_at=role.created_at,
        )


class SurveyMemberResponses(APIResponseModel):
    """Embedded user details on a survey member row."""

    model_config = ConfigDict(from_attributes=True)

    id: ProjectMembershipId
    user_id: UserId
    project_id: ProjectId
    role_id: ProjectRoleId | None
    status: ProjectMemberStatus


class SurveyMemberRoleResponses(APIResponseModel):
    """API response shape for a survey membership role assignment."""

    model_config = ConfigDict(from_attributes=True)

    project_id: ProjectId
    survey_id: SurveyId
    membership_id: ProjectMembershipId
    role_id: SurveyRoleId
    created_at: Timestamp
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
