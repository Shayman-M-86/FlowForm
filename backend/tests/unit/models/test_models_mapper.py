"""Tests for SQLAlchemy model mapper configuration.

The cycle test is the most important: Survey → SurveyVersion → Survey.
Run this immediately after any change to survey.py.
"""

from typing import Any, cast

from sqlalchemy import inspect
from sqlalchemy.orm import Mapper, configure_mappers


def test_configure_mappers_no_errors() -> None:
    """All models can be fully mapped without circular dependency errors."""
    import app.models  # noqa: F401 — registers all mappers

    # Raises if any relationship target is unresolvable or the mapper graph is broken
    configure_mappers()



def test_survey_version_cycle_relationships_resolve() -> None:
    """Survey.versions, Survey.published_version, and SurveyVersion.survey all resolve."""
    import app.models  # noqa: F401

    configure_mappers()

    from app.models import Survey, SurveyVersion

    survey_mapper = cast(Mapper[Any], inspect(Survey))
    version_mapper = cast(Mapper[Any], inspect(SurveyVersion))

    survey_rel_names = {r.key for r in survey_mapper.relationships}
    version_rel_names = {r.key for r in version_mapper.relationships}

    assert "versions" in survey_rel_names, "Survey.versions relationship missing"
    assert "published_version" in survey_rel_names, "Survey.published_version relationship missing"
    assert "survey" in version_rel_names, "SurveyVersion.survey relationship missing"


