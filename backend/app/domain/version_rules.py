from collections.abc import Iterator

from app.domain.errors import (
    SurveyPublishError,
    VersionAlreadyArchivedError,
    VersionIsActivePublishedError,
    VersionNotEditableError,
    VersionNotPublishedError,
)
from app.schema.models.survey_document.conditions import (
    AllCondition,
    AnyCondition,
    Condition,
    ConditionalVisibility,
    NotCondition,
)
from app.schema.models.survey_document.document import InputBlock
from app.schema.orm.core.survey import Survey, SurveyVersion
from app.schema.types import SurveyFieldUuid


def ensure_is_draft(*, version: SurveyVersion) -> None:
    if version.status != "draft":
        raise SurveyPublishError(f"Cannot publish a version with status '{version.status}'")


def _condition_field_ids(condition: Condition) -> Iterator[SurveyFieldUuid]:
    if isinstance(condition, AllCondition):
        for item in condition.all:
            yield from _condition_field_ids(item)
    elif isinstance(condition, AnyCondition):
        for item in condition.any:
            yield from _condition_field_ids(item)
    elif isinstance(condition, NotCondition):
        yield from _condition_field_ids(condition.condition)
    else:
        yield condition.fieldUuid


def ensure_publishable(*, version: SurveyVersion) -> None:
    content = version.content
    if content is None:
        raise SurveyPublishError("Cannot publish a version with no survey content")

    fields: set[SurveyFieldUuid] = set()
    conditions: list[Condition] = []
    for section in content.sections:
        for block in section.blocks:
            if not isinstance(block, InputBlock):
                continue
            field = block.field
            if field.uuid in fields:
                raise SurveyPublishError("Survey field UUIDs must be unique within a version")
            fields.add(field.uuid)
            visibility = field.behaviour.visibility if field.behaviour is not None else None
            if isinstance(visibility, ConditionalVisibility):
                conditions.append(visibility.condition)
    if content.workflow is not None:
        conditions.extend(rule.when for rule in content.workflow.rules)
    if any(field_id not in fields for condition in conditions for field_id in _condition_field_ids(condition)):
        raise SurveyPublishError("Survey conditions must reference fields in the same version")


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
