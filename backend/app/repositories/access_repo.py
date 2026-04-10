from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.schema.orm.core import ProjectMembership, ProjectRole, SurveyMembershipRole, SurveyRole


def get_survey_membership_role(
    db: Session,
    *,
    project_id: int,
    survey_id: int,
    membership_id: int,
) -> SurveyMembershipRole | None:
    return db.scalar(
        select(SurveyMembershipRole)
        .options(selectinload(SurveyMembershipRole.role).selectinload(SurveyRole.permissions))
        .where(
            SurveyMembershipRole.project_id == project_id,
            SurveyMembershipRole.survey_id == survey_id,
            SurveyMembershipRole.membership_id == membership_id,
        )
    )


def get_project_membership(
    db: Session,
    *,
    project_id: int,
    user_id: int,
) -> ProjectMembership | None:
    return db.scalar(
        select(ProjectMembership)
        .options(selectinload(ProjectMembership.role).selectinload(ProjectRole.permissions))
        .where(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == user_id,
        )
    )
