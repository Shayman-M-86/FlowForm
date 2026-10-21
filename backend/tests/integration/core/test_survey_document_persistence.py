"""Database protections and replacement semantics for stored survey documents."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.error_handling import flush_with_err_handle
from app.repositories import surveys_repo
from app.schema.orm.core.survey import SurveyVersion
from tests.survey_document import make_definition


def test_replace_document_advances_revision_and_persists(db_session: Session, survey_version: SurveyVersion) -> None:
    replacement = make_definition()
    replacement["document"]["sections"][0]["title"] = "Changed"
    previous_revision = survey_version.revision
    surveys_repo.replace_definition(db_session, survey_version, replacement)
    db_session.refresh(survey_version)
    assert survey_version.definition == replacement
    assert survey_version.revision == previous_revision + 1


def test_published_document_cannot_be_changed(db_session: Session, survey_version: SurveyVersion) -> None:
    survey_version.status = "published"
    survey_version.published_at = datetime.now(UTC)
    db_session.flush()
    replacement = make_definition()
    replacement["document"]["sections"][0]["title"] = "Changed after publishing"
    survey_version.definition = replacement
    with pytest.raises(AppError) as exc_info:
        flush_with_err_handle(db_session, contexts=[survey_version])
    assert exc_info.value.code == "VERSION_DEFINITION_LOCKED"
    assert exc_info.value.status_code == 409
