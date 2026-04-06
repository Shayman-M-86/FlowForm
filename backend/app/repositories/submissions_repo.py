from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schema.orm.core.survey_submission import SurveySubmission


def list_submissions(
    db: Session,
    *,
    project_id: int,
    survey_id: int | None = None,
    status: str | None = None,
    submission_channel: str | None = None,
) -> list[SurveySubmission]:
    query = select(SurveySubmission).where(SurveySubmission.project_id == project_id)

    if survey_id is not None:
        query = query.where(SurveySubmission.survey_id == survey_id)

    if status is not None:
        query = query.where(SurveySubmission.status == status)

    if submission_channel is not None:
        query = query.where(SurveySubmission.submission_channel == submission_channel)

    return list(db.scalars(query))
