"""Conversions between typed application documents and their JSONB storage."""

from typing import Any

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator

from app.schema.models.survey_document import SurveyDefinition


class SurveyDefinitionJSONB(TypeDecorator[SurveyDefinition]):
    """Store JSON data and reconstruct the canonical survey definition on load."""

    impl = JSONB
    cache_ok = True

    def process_bind_param(self, value: SurveyDefinition | None, dialect: Dialect) -> dict[str, Any] | None:  # noqa: ARG002
        """Serialize a typed definition before the underlying JSONB encoding."""
        if value is None:
            return None
        return value.model_dump(mode="json", by_alias=True)

    def process_result_value(self, value: Any, dialect: Dialect) -> SurveyDefinition | None:  # noqa: ARG002
        """Validate stored JSON at the database-to-application boundary."""
        if value is None:
            return None
        return SurveyDefinition.model_validate(value)
