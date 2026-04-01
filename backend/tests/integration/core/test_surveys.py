from __future__ import annotations

from typing import cast

import pytest
from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from app.models.core.survey import Survey
from app.models.core.user import User
from tests.integration.core.factories import make_survey_version


def test_survey_version_unique_version_number_per_survey(
    db_session: scoped_session[Session], survey: Survey, user: User
) -> None:
    version_a = make_survey_version(survey.id, user.id, version_number=1)
    db_session.add(version_a)
    db_session.flush()

    version_b = make_survey_version(survey.id, user.id, version_number=1)
    db_session.add(version_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    assert constraint == "uq_survey_versions_survey_id_version_number", (
        f"Expected constraint 'uq_survey_versions_survey_id_version_number', got '{constraint}'\n"
        f"DB error: {exc_info.value}"
    )

    db_session.rollback()
