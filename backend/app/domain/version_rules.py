from app.domain.errors import (
    SurveyPublishError,
    VersionAlreadyArchivedError,
    VersionIsActivePublishedError,
    VersionNotEditableError,
    VersionNotFoundError,
    VersionNotPublishedError,
)
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.orm.core.survey_content import SurveyQuestion


def ensure_is_draft(*, version: SurveyVersion) -> None:
    if version.status != "draft":
        raise SurveyPublishError(f"Cannot publish a version with status '{version.status}'")


def ensure_has_questions(*, questions: list[SurveyQuestion]) -> None:
    if not questions:
        raise SurveyPublishError("Cannot publish a version with no questions")


def ensure_can_archive(*, version: SurveyVersion) -> None:
    if version.status == "archived":
        raise VersionAlreadyArchivedError()


def ensure_is_published(*, version: SurveyVersion) -> None:
    if version.status != "published":
        raise VersionNotPublishedError()


def ensure_is_not_active_published(*, survey: Survey, version: SurveyVersion) -> None:
    if survey.published_version_id == version.id:
        raise VersionIsActivePublishedError()


def ensure_is_editable(*, version: SurveyVersion) -> None:
    if version.status != "draft":
        raise VersionNotEditableError(status=version.status)


def ensure_not_none(*, version: SurveyVersion | None, version_number: int, survey_id: int) -> SurveyVersion:
    if version is None:
        raise VersionNotFoundError(survey_id=survey_id, version_number=version_number)
    return version
