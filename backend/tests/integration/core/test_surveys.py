from __future__ import annotations

import pytest
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

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()
