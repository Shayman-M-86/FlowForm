from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CoreBase
from app.schema.orm.base import TimestampMixin

if TYPE_CHECKING:
    from app.schema.orm.core.survey import SurveyVersion

class SurveyQuestion(TimestampMixin, CoreBase):
    """A single question definition within a survey version."""

    __tablename__ = "survey_questions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    survey_version_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("survey_versions.id", ondelete="CASCADE"), nullable=False
    )
    question_key: Mapped[str] = mapped_column(Text, nullable=False)
    question_schema: Mapped[dict] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        UniqueConstraint("survey_version_id", "question_key", name="uq_survey_questions_version_key"),
        CheckConstraint("jsonb_typeof(question_schema) = 'object'", name="question_schema_is_object"),
        CheckConstraint(
            "question_schema->>'type' IN ('choice', 'field', 'matching', 'rating')",
            name="question_type_valid",
        ),
    )

    survey_version: Mapped[SurveyVersion] = relationship(
        "SurveyVersion", foreign_keys=[survey_version_id]
    )


class SurveyRule(TimestampMixin, CoreBase):
    """A branching or visibility rule attached to a survey version."""

    __tablename__ = "survey_rules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    survey_version_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("survey_versions.id", ondelete="CASCADE"), nullable=False
    )
    rule_key: Mapped[str] = mapped_column(Text, nullable=False)
    rule_schema: Mapped[dict] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        UniqueConstraint("survey_version_id", "rule_key", name="uq_survey_rules_version_key"),
        CheckConstraint("jsonb_typeof(rule_schema) = 'object'", name="rule_schema_is_object"),
    )

    survey_version: Mapped[SurveyVersion] = relationship(
        "SurveyVersion", foreign_keys=[survey_version_id]
    )


class SurveyScoringRule(TimestampMixin, CoreBase):
    """A scoring rule attached to a survey version."""

    __tablename__ = "survey_scoring_rules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    survey_version_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("survey_versions.id", ondelete="CASCADE"), nullable=False
    )
    scoring_key: Mapped[str] = mapped_column(Text, nullable=False)
    scoring_schema: Mapped[dict] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        UniqueConstraint("survey_version_id", "scoring_key", name="uq_survey_scoring_rules_version_key"),
        CheckConstraint("jsonb_typeof(scoring_schema) = 'object'", name="scoring_schema_is_object"),
    )

    survey_version: Mapped[SurveyVersion] = relationship(
        "SurveyVersion", foreign_keys=[survey_version_id]
    )
