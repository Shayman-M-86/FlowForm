from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.schema.orm.core.survey_submission import SurveySubmission


def list_submissions(
    db: Session,
    *,
    project_id: int,
    survey_id: int | None = None,
    status: str | None = None,
    submission_channel: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[SurveySubmission], int]:
    filters = [SurveySubmission.project_id == project_id]

    if survey_id is not None:
        filters.append(SurveySubmission.survey_id == survey_id)

    if status is not None:
        filters.append(SurveySubmission.status == status)

    if submission_channel is not None:
        filters.append(SurveySubmission.submission_channel == submission_channel)

    total = db.scalar(select(func.count()).select_from(SurveySubmission).where(*filters)) or 0

    offset = (page - 1) * page_size

    items = list(
        db.scalars(
            select(SurveySubmission)
            .where(*filters)
            .order_by(SurveySubmission.id.desc())
            .limit(page_size)
            .offset(offset)
        )
    )

    return items, total
