"""Conversions between typed application documents and their JSONB storage."""

from typing import Any

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

from app.schema.models.survey_document import SurveyContent


class SurveyContentJSONB(TypeDecorator[SurveyContent]):
    """Store JSON data and reconstruct the survey content on load."""

    impl = JSONB(none_as_null=True)
    cache_ok = True

    def process_bind_param(self, value: SurveyContent | None, dialect: Dialect) -> dict[str, Any] | None:  # noqa: ARG002
        """Serialize a content model before the underlying JSONB encoding."""
        if value is None:
            return None
        return value.model_dump(mode="json", by_alias=True)

    def process_result_value(self, value: Any, dialect: Dialect) -> SurveyContent | None:  # noqa: ARG002
        """Validate stored JSON at the database-to-application boundary."""
        if value is None:
            return None
        return SurveyContent.model_validate(value)
