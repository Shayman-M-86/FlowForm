from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.extensions import db
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.core.survey import SurveyVersion

class SurveyQuestion(TimestampMixin, db.Model):
    """A single question definition within a survey version."""

    __tablename__ = "survey_questions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    survey_version_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("survey_versions.id", ondelete="CASCADE"), nullable=False
    )
    question_key: Mapped[str] = mapped_column(Text, nullable=False)
    question_schema: Mapped[dict] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "survey_version_id", "question_key", name="uq_survey_questions_version_key"
        ),
    )

    survey_version: Mapped[SurveyVersion] = relationship(
        "SurveyVersion", foreign_keys=[survey_version_id]
    )


class SurveyRule(TimestampMixin, db.Model):
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
    )

    survey_version: Mapped[SurveyVersion] = relationship(
        "SurveyVersion", foreign_keys=[survey_version_id]
    )


class SurveyScoringRule(TimestampMixin, db.Model):
    """A scoring rule attached to a survey version."""

    __tablename__ = "survey_scoring_rules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    survey_version_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("survey_versions.id", ondelete="CASCADE"), nullable=False
    )
    scoring_key: Mapped[str] = mapped_column(Text, nullable=False)
    scoring_schema: Mapped[dict] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "survey_version_id", "scoring_key", name="uq_survey_scoring_rules_version_key"
        ),
    )

    survey_version: Mapped[SurveyVersion] = relationship(
        "SurveyVersion", foreign_keys=[survey_version_id]
    )
