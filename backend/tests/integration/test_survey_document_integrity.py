"""Exercise the document constraints in the PostgreSQL bootstrap schema."""

from datetime import UTC, datetime

import pytest
from psycopg.errors import CheckViolation
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
from app.db.error_handling.errors import DbIntegrityError
from app.schema.models.survey_document.document import SurveyDefinition, SurveyDocument
from app.schema.orm.core import Project, Survey, SurveyVersion
from app.schema.types import SurveyVersionId


@pytest.fixture
def draft(core_db_session: Session) -> SurveyVersion:
    project = Project(name="Integrity tests", slug="integrity-tests")
    core_db_session.add(project)
    core_db_session.flush()
    survey = Survey(project_id=project.id, title="Test survey")
    core_db_session.add(survey)
    core_db_session.flush()
    version = SurveyVersion(survey_id=survey.id, version_number=1)
    core_db_session.add(version)
    core_db_session.flush()
    return version


def _definition(version_id: SurveyVersionId) -> SurveyDefinition:
    return SurveyDefinition(
        id="test-survey",
        versionId=version_id,
        revision=1,
        title="Test survey",
        projectName="Integrity tests",
        status="published",
        document=SurveyDocument(sections=[]),
    )


def test_empty_draft_stores_database_null(core_db_session: Session, draft: SurveyVersion) -> None:
    assert (
        core_db_session.scalar(text("SELECT definition IS NULL FROM survey_versions WHERE id = :id"), {"id": draft.id})
        is True
    )


@pytest.mark.parametrize("value", ["[]", "null"])
def test_definition_rejects_non_object_json(core_db_session: Session, draft: SurveyVersion, value: str) -> None:
    with pytest.raises(IntegrityError) as error:
        core_db_session.execute(
            text("UPDATE survey_versions SET definition = CAST(:value AS jsonb) WHERE id = :id"),
            {"value": value, "id": draft.id},
        )

    assert isinstance(error.value.orig, CheckViolation)
    assert error.value.orig.diag.constraint_name == "ck_survey_versions_definition_is_object"


@pytest.mark.parametrize("missing", ["definition", "timestamp"])
def test_publish_requires_document_and_timestamp(core_db_session: Session, draft: SurveyVersion, missing: str) -> None:
    draft.status = "published"
    if missing == "definition":
        draft.published_at = datetime.now(UTC)
    else:
        draft.definition = _definition(draft.id)

    with pytest.raises(DbIntegrityError) as error:
        flush_with_err_handle(core_db_session, contexts=[draft])

    assert error.value.constraint_name == "ck_survey_versions_published_requires_definition_and_timestamp"
    assert (error.value.status_code, error.value.code) == (500, "VERSION_PUBLISH_STATE_INVALID")


@pytest.mark.parametrize("status", ["published", "archived"])
def test_non_draft_definition_is_locked(core_db_session: Session, draft: SurveyVersion, status: str) -> None:
    definition = _definition(draft.id)
    draft.definition = definition
    draft.published_at = datetime.now(UTC)
    draft.status = "published"
    core_db_session.flush()
    if status == "archived":
        draft.status = "archived"
        core_db_session.flush()

    draft.definition = definition.model_copy(update={"title": "Edited"})
    with pytest.raises(DbIntegrityError) as error:
        flush_with_err_handle(core_db_session, contexts=[draft])

    assert (error.value.status_code, error.value.code) == (409, "VERSION_NOT_EDITABLE")
