from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
from app.schema.api.requests.surveys import CreateSurveyRequest, UpdateSurveyRequest
from app.schema.orm.core.survey import Survey, SurveyVersion


def list_surveys(db: Session, project_id: int) -> list[Survey]:
    return list(db.scalars(select(Survey).where(Survey.project_id == project_id)))


def list_surveys_ids(db: Session, project_id: int) -> list[int]:
    return list(db.scalars(select(Survey.id).where(Survey.project_id == project_id)))


def get_survey(db: Session, project_id: int, survey_id: int) -> Survey | None:
    return db.scalar(select(Survey).where(Survey.project_id == project_id, Survey.id == survey_id))


def create_survey(
    db: Session,
    project_id: int,
    data: CreateSurveyRequest,
    created_by_user_id: int | None = None,
) -> Survey:
    survey = Survey(
        project_id=project_id,
        title=data.title,
        visibility=data.visibility,
        public_slug=data.public_slug,
        default_response_store_id=data.default_response_store_id,
        created_by_user_id=created_by_user_id,
    )
    db.add(survey)
    flush_with_err_handle(db, contexts=[survey])
    return survey


def update_survey(db: Session, survey: Survey, data: UpdateSurveyRequest) -> Survey:
    changed = data.model_fields_set
    if "title" in changed and data.title is not None:
        survey.title = data.title
    if "visibility" in changed and data.visibility is not None:
        survey.visibility = data.visibility
    if "public_slug" in changed:
        survey.public_slug = data.public_slug
    if "default_response_store_id" in changed:
        survey.default_response_store_id = data.default_response_store_id
    flush_with_err_handle(db, contexts=[survey])
    return survey


def delete_survey(db: Session, survey: Survey) -> None:
    db.delete(survey)
    flush_with_err_handle(db, contexts=[survey])


def list_versions(db: Session, survey_id: int) -> list[SurveyVersion]:
    return list(
        db.scalars(
            select(SurveyVersion)
            .where(SurveyVersion.survey_id == survey_id, SurveyVersion.deleted_at.is_(None))
            .order_by(SurveyVersion.version_number)
        )
    )


def get_version(db: Session, project_id: int, survey_id: int, version_number: int) -> SurveyVersion | None:
    return db.scalar(
        select(SurveyVersion)
        .join(Survey, Survey.id == SurveyVersion.survey_id)
        .where(
            Survey.project_id == project_id,
            SurveyVersion.survey_id == survey_id,
            SurveyVersion.version_number == version_number,
            SurveyVersion.deleted_at.is_(None),
        )
    )


def create_version(db: Session, survey_id: int, created_by_user_id: int | None = None) -> SurveyVersion:
    max_num = db.scalar(select(func.max(SurveyVersion.version_number)).where(SurveyVersion.survey_id == survey_id)) or 0
    version = SurveyVersion(
        survey_id=survey_id,
        version_number=max_num + 1,
        status="draft",
        created_by_user_id=created_by_user_id,
    )
    db.add(version)
    flush_with_err_handle(db, contexts=[version])
    return version


def publish_version(
    db: Session,
    survey: Survey,
    version: SurveyVersion,
    compiled_schema: dict,
) -> SurveyVersion:
    if survey.published_version_id and survey.published_version_id != version.id:
        current = db.get(SurveyVersion, survey.published_version_id)
        if current is not None:
            survey.published_version_id = None
            flush_with_err_handle(db, contexts=[survey, current])
            current.status = "archived"
            flush_with_err_handle(db, contexts=[current, survey])

    version.status = "published"
    version.compiled_schema = compiled_schema
    version.published_at = datetime.now(UTC)

    # SQLAlchemy flushes all dirty session objects together, so pass both as
    # contexts so any integrity error on either is correctly translated.
    flush_with_err_handle(db, contexts=[version, survey])

    survey.published_version_id = version.id
    flush_with_err_handle(db, contexts=[survey, version])

    return version


def archive_version(db: Session, version: SurveyVersion) -> SurveyVersion:
    version.status = "archived"
    flush_with_err_handle(db, contexts=[version])
    return version


def unpublish_version(db: Session, survey: Survey, version: SurveyVersion) -> SurveyVersion:
    survey.published_version_id = None
    flush_with_err_handle(db, contexts=[survey, version])

    version.status = "archived"
    flush_with_err_handle(db, contexts=[version, survey])
    return version


def list_public_surveys(db: Session, *, page: int, page_size: int) -> tuple[list[Survey], int]:
    base = select(Survey).where(Survey.visibility == "public")
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    surveys = list(
        db.scalars(
            base.order_by(Survey.id).offset((page - 1) * page_size).limit(page_size)
        )
    )
    return surveys, total


def get_by_public_slug(db: Session, public_slug: str) -> Survey | None:
    return db.scalar(select(Survey).where(Survey.public_slug == public_slug, Survey.visibility == "public"))


def get_published_version(db: Session, survey: Survey) -> SurveyVersion | None:
    if survey.published_version_id is None:
        return None

    return db.scalar(select(SurveyVersion).where(SurveyVersion.id == survey.published_version_id))
