from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.error_handling import flush_with_err_handle
from app.schema.orm.core.project import ProjectMembership
from app.schema.orm.core.survey_access import SurveyMembershipRole, SurveyRole


def list_by_survey(db: Session, *, project_id: int, survey_id: int) -> list[SurveyMembershipRole]:
    return list(
        db.scalars(
            select(SurveyMembershipRole)
            .options(
                selectinload(SurveyMembershipRole.membership).selectinload(ProjectMembership.user),
                selectinload(SurveyMembershipRole.role).selectinload(SurveyRole.permissions),
            )
            .where(
                SurveyMembershipRole.project_id == project_id,
                SurveyMembershipRole.survey_id == survey_id,
            )
            .order_by(SurveyMembershipRole.created_at.asc())
        )
    )


def get_by_membership(
    db: Session,
    *,
    project_id: int,
    survey_id: int,
    membership_id: int,
) -> SurveyMembershipRole | None:
    return db.scalar(
        select(SurveyMembershipRole)
        .options(
            selectinload(SurveyMembershipRole.membership).selectinload(ProjectMembership.user),
            selectinload(SurveyMembershipRole.role).selectinload(SurveyRole.permissions),
        )
        .where(
            SurveyMembershipRole.project_id == project_id,
            SurveyMembershipRole.survey_id == survey_id,
            SurveyMembershipRole.membership_id == membership_id,
        )
    )


def create_assignment(
    db: Session,
    *,
    project_id: int,
    survey_id: int,
    membership_id: int,
    role_id: int,
) -> SurveyMembershipRole:
    assignment = SurveyMembershipRole(
        project_id=project_id,
        survey_id=survey_id,
        membership_id=membership_id,
        role_id=role_id,
    )
    db.add(assignment)
    flush_with_err_handle(db, contexts=[assignment])
    return assignment


def update_assignment(
    db: Session,
    assignment: SurveyMembershipRole,
    *,
    role_id: int,
) -> SurveyMembershipRole:
    assignment.role_id = role_id
    flush_with_err_handle(db, contexts=[assignment])
    return assignment


def delete_assignment(db: Session, assignment: SurveyMembershipRole) -> None:
    db.delete(assignment)
    flush_with_err_handle(db, contexts=[assignment])
