from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db.error_handling import flush_with_err_handle
from app.schema.enums import SurveyVisibility
from app.schema.models.survey_document import SurveyContent
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.types import (
    Count,
    DocumentRevision,
    PageNumber,
    PageSize,
    ProjectId,
    ResponseStoreId,
    Slug,
    SurveyId,
    SurveyTitle,
    SurveyVersionId,
    SurveyVersionNumber,
    UserId,
)


def list_surveys(db: Session, project_id: ProjectId) -> list[Survey]:
    return list(db.scalars(select(Survey).where(Survey.project_id == project_id)))


def list_surveys_ids(db: Session, project_id: ProjectId) -> list[SurveyId]:
    return list(db.scalars(select(Survey.id).where(Survey.project_id == project_id)))


def get_survey(db: Session, project_id: ProjectId, survey_id: SurveyId) -> Survey | None:
    return db.scalar(select(Survey).where(Survey.project_id == project_id, Survey.id == survey_id))


def create_survey(
    db: Session,
    project_id: ProjectId,
    *,
    title: SurveyTitle,
    visibility: SurveyVisibility,
    public_slug: Slug | None,
    default_response_store_id: ResponseStoreId,
    created_by_user_id: UserId | None = None,
) -> Survey:
    survey = Survey(
        project_id=project_id,
        title=title,
        visibility=visibility,
        public_slug=public_slug,
        default_response_store_id=default_response_store_id,
        created_by_user_id=created_by_user_id,
    )
    db.add(survey)
    flush_with_err_handle(db, contexts=[survey])
    return survey


def update_survey(
    db: Session,
    survey: Survey,
    *,
    title: SurveyTitle,
    visibility: SurveyVisibility,
    public_slug: Slug | None,
) -> Survey:
    survey.title = title
    survey.visibility = visibility
    survey.public_slug = public_slug
    flush_with_err_handle(db, contexts=[survey])
    return survey


def delete_survey(db: Session, survey: Survey) -> None:
    db.delete(survey)
    flush_with_err_handle(db, contexts=[survey])


def list_versions(db: Session, survey_id: SurveyId) -> list[SurveyVersion]:
    return list(
        db.scalars(
            select(SurveyVersion)
            .where(SurveyVersion.survey_id == survey_id, SurveyVersion.deleted_at.is_(None))
            .order_by(SurveyVersion.version_number)
        )
    )


def _version_query(project_id: ProjectId, survey_id: SurveyId):
    return (
        select(SurveyVersion)
        .join(Survey, Survey.id == SurveyVersion.survey_id)
        .where(
            Survey.project_id == project_id,
            SurveyVersion.survey_id == survey_id,
            SurveyVersion.deleted_at.is_(None),
        )
    )


def get_version(
    db: Session,
    project_id: ProjectId,
    survey_id: SurveyId,
    version_number: SurveyVersionNumber,
    *,
    for_update: bool = False,
) -> SurveyVersion | None:
    query = _version_query(project_id, survey_id).where(SurveyVersion.version_number == version_number)
    if for_update:
        query = query.with_for_update(of=SurveyVersion).execution_options(populate_existing=True)
    return db.scalar(query)


def lock_version_by_id(
    db: Session, project_id: ProjectId, survey_id: SurveyId, version_id: SurveyVersionId
) -> SurveyVersion | None:
    """Lock the scoped version so concurrent saves see the latest revision."""
    query = (
        _version_query(project_id, survey_id)
        .where(SurveyVersion.id == version_id)
        .with_for_update(of=SurveyVersion)
        .execution_options(populate_existing=True)
    )
    return db.scalar(query)


def get_content(
    db: Session, project_id: ProjectId, survey_id: SurveyId, version_number: SurveyVersionNumber
) -> SurveyContent | None:
    """Read independent content for a scoped version."""
    version = get_version(db, project_id, survey_id, version_number)
    if version is None or version.content is None:
        return None
    return version.content.model_copy(deep=True)


def update_content(db: Session, version: SurveyVersion, content: SurveyContent, revision: DocumentRevision) -> None:
    """Replace the entire JSONB value and write the new revision together."""
    version.content = content.model_copy(deep=True)
    version.revision = revision
    flag_modified(version, "content")
    flush_with_err_handle(db, contexts=[version])


def create_version(
    db: Session,
    survey_id: SurveyId,
    *,
    created_by_user_id: UserId | None = None,
    content: SurveyContent | None = None,
    revision: DocumentRevision = 0,
) -> SurveyVersion:
    max_num = db.scalar(select(func.max(SurveyVersion.version_number)).where(SurveyVersion.survey_id == survey_id)) or 0
    version = SurveyVersion(
        survey_id=survey_id,
        version_number=max_num + 1,
        status="draft",
        created_by_user_id=created_by_user_id,
        content=content.model_copy(deep=True) if content is not None else None,
        revision=revision,
    )
    db.add(version)
    flush_with_err_handle(db, contexts=[version])
    return version


def publish_version(
    db: Session,
    survey: Survey,
    version: SurveyVersion,
) -> SurveyVersion:
    if survey.published_version_id and survey.published_version_id != version.id:
        current = db.get(SurveyVersion, survey.published_version_id)
        if current is not None:
            survey.published_version_id = None
            flush_with_err_handle(db, contexts=[survey, current])
            current.status = "archived"
            flush_with_err_handle(db, contexts=[current, survey])

    version.status = "published"
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


def list_public_surveys(db: Session, *, page: PageNumber, page_size: PageSize) -> tuple[list[Survey], Count]:
    base = select(Survey).where(Survey.visibility == "public")
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    surveys = list(db.scalars(base.order_by(Survey.id).offset((page - 1) * page_size).limit(page_size)))
    return surveys, total


def get_by_public_slug(db: Session, public_slug: Slug) -> Survey | None:
    return db.scalar(select(Survey).where(Survey.public_slug == public_slug, Survey.visibility == "public"))


def get_published_version(db: Session, survey: Survey) -> SurveyVersion | None:
    if survey.published_version_id is None:
        return None

    return db.scalar(select(SurveyVersion).where(SurveyVersion.id == survey.published_version_id))
