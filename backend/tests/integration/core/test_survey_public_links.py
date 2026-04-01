from __future__ import annotations

from typing import cast

import pytest
from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session

from app.models.core.survey import Survey
from app.models.core.survey_access import SurveyPublicLink
from tests.integration.core.factories import make_token_pair


def test_survey_public_link_unique_token_hash(db_session: scoped_session[Session], survey: Survey) -> None:
    # link_a and link_b have different prefixes but the same hash.
    # Only the token_hash unique constraint can fire here.
    _, prefix_a, token_hash = make_token_pair()

    link_a = SurveyPublicLink()
    link_a.survey_id = survey.id
    link_a.token_prefix = prefix_a
    link_a.token_hash = token_hash
    db_session.add(link_a)
    db_session.flush()

    _, prefix_b, _ = make_token_pair()

    link_b = SurveyPublicLink()
    link_b.survey_id = survey.id
    link_b.token_prefix = prefix_b
    link_b.token_hash = token_hash
    db_session.add(link_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    
    assert constraint == "uq_survey_public_links_token_hash", (
        f"Wrong constraint triggered.\n"
        f"Expected: uq_survey_public_links_token_hash\n"
        f"Actual:   {constraint}\n\n"
        f"DB error: {exc_info.value}"
    )
    db_session.rollback()


def test_survey_public_link_unique_prefix_within_survey(db_session: scoped_session[Session], survey: Survey) -> None:
    # link_a and link_b have the same prefix but different hashes.
    # Only the (survey_id, token_prefix) unique constraint can fire here.
    _, token_prefix, hash_a = make_token_pair()

    link_a = SurveyPublicLink()
    link_a.survey_id = survey.id
    link_a.token_prefix = token_prefix
    link_a.token_hash = hash_a
    db_session.add(link_a)
    db_session.flush()

    _, _, hash_b = make_token_pair()

    link_b = SurveyPublicLink()
    link_b.survey_id = survey.id
    link_b.token_prefix = token_prefix
    link_b.token_hash = hash_b
    db_session.add(link_b)

    with pytest.raises(IntegrityError) as exc_info:
        db_session.flush()

    orig = cast(UniqueViolation, exc_info.value.orig)
    constraint = orig.diag.constraint_name
    
    
    assert constraint == "uq_survey_public_links_survey_id_token_prefix", (
    f"Wrong constraint triggered.\n"
    f"Expected: uq_survey_public_links_survey_id_token_prefix\n"
    f"Actual:   {constraint}\n\n"
    f"DB error: {exc_info.value}"
)

    db_session.rollback()
