from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.schema.api.requests.surveys import CreateSurveyRequest, UpdateSurveyRequest
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.survey_content import SurveyQuestion, SurveyRule, SurveyScoringRule


def list_surveys(db: Session, project_id: int) -> list[Survey]:
    return list(db.scalars(select(Survey).where(Survey.project_id == project_id)))


def get_survey(db: Session, project_id: int, survey_id: int) -> Survey | None:
    return db.scalar(
        select(Survey).where(Survey.project_id == project_id, Survey.id == survey_id)
    )


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
        allow_public_responses=data.allow_public_responses,
        public_slug=data.public_slug,
        default_response_store_id=data.default_response_store_id,
        created_by_user_id=created_by_user_id,
    )
    db.add(survey)
    db.flush()
    return survey


def update_survey(db: Session, survey: Survey, data: UpdateSurveyRequest) -> Survey:
    changed = data.model_fields_set
    if "title" in changed and data.title is not None:
        survey.title = data.title
    if "visibility" in changed and data.visibility is not None:
        survey.visibility = data.visibility
    if "allow_public_responses" in changed and data.allow_public_responses is not None:
        survey.allow_public_responses = data.allow_public_responses
    if "public_slug" in changed:
        survey.public_slug = data.public_slug
    if "default_response_store_id" in changed:
        survey.default_response_store_id = data.default_response_store_id
    db.flush()
    return survey


def delete_survey(db: Session, survey: Survey) -> None:
    db.delete(survey)
    db.flush()


def list_versions(db: Session, survey_id: int) -> list[SurveyVersion]:
    return list(
        db.scalars(
            select(SurveyVersion)
            .where(SurveyVersion.survey_id == survey_id, SurveyVersion.deleted_at.is_(None))
            .order_by(SurveyVersion.version_number)
        )
    )


def get_version(db: Session, survey_id: int, version_id: int) -> SurveyVersion | None:
    return db.scalar(
        select(SurveyVersion).where(
            SurveyVersion.survey_id == survey_id,
            SurveyVersion.id == version_id,
            SurveyVersion.deleted_at.is_(None),
        )
    )


def create_version(
    db: Session, survey_id: int, created_by_user_id: int | None = None
) -> SurveyVersion:
    max_num = (
        db.scalar(
            select(func.max(SurveyVersion.version_number)).where(
                SurveyVersion.survey_id == survey_id
            )
        )
        or 0
    )
    version = SurveyVersion(
        survey_id=survey_id,
        version_number=max_num + 1,
        status="draft",
        created_by_user_id=created_by_user_id,
    )
    db.add(version)
    db.flush()
    return version


def publish_version(db: Session, survey: Survey, version: SurveyVersion) -> SurveyVersion:
    if version.status != "draft":
        raise ValueError(f"Cannot publish a version with status '{version.status}'")

    questions = list(
        db.scalars(
            select(SurveyQuestion).where(SurveyQuestion.survey_version_id == version.id)
        )
    )
    if not questions:
        raise ValueError("Cannot publish a version with no questions")

    rules = list(
        db.scalars(select(SurveyRule).where(SurveyRule.survey_version_id == version.id))
    )
    scoring_rules = list(
        db.scalars(
            select(SurveyScoringRule).where(SurveyScoringRule.survey_version_id == version.id)
        )
    )

    compiled = {
        "questions": [{"key": q.question_key, "schema": q.question_schema} for q in questions],
        "rules": [{"key": r.rule_key, "schema": r.rule_schema} for r in rules],
        "scoring_rules": [
            {"key": s.scoring_key, "schema": s.scoring_schema} for s in scoring_rules
        ],
    }

    # Archive the current published version before promoting this one
    if survey.published_version_id:
        current = db.scalar(
            select(SurveyVersion).where(SurveyVersion.id == survey.published_version_id)
        )
        if current:
            current.status = "archived"

    version.status = "published"
    version.compiled_schema = compiled
    version.published_at = datetime.now(UTC)
    survey.published_version_id = version.id

    db.flush()
    return version


def archive_version(db: Session, version: SurveyVersion) -> SurveyVersion:
    if version.status == "archived":
        raise ValueError("Version is already archived")
    version.status = "archived"
    db.flush()
    return version

def get_published_version(db: Session, survey: Survey) -> SurveyVersion | None:
    if survey.published_version_id is None:
        return None

    return db.scalar(select(SurveyVersion).where(SurveyVersion.id == survey.published_version_id))