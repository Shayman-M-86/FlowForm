import uuid
from typing import TYPE_CHECKING, Literal

from sqlalchemy import BigInteger, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import CoreBase
from app.schema.orm.base import TimestampMixin

if TYPE_CHECKING:
    from app.schema.orm.core.survey import SurveyVersion

SurveyNodeType = Literal["question", "rule"]


class SurveyQuestion(TimestampMixin, CoreBase):
    """An ordered survey node within a survey version.

    This table keeps the historical `survey_questions` name, but rows can now
    represent either question nodes or rule nodes.

    `id` is the globally unique node id used by submission events.
    `question_key` is the stable human-readable node key:
    - question node: "q1", "q2", etc.
    - rule node: "r1", "r2", etc.
    """

    __tablename__ = "survey_questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())

    survey_version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("survey_versions.id", ondelete="CASCADE"),
        nullable=False,
    )

    question_key: Mapped[str] = mapped_column(Text, nullable=False)
    sort_key: Mapped[int] = mapped_column(Integer, nullable=False)
    node_type: Mapped[SurveyNodeType] = mapped_column(Text, nullable=False)
    question_schema: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Only necessary constraints live in SQLAlchemy; source of truth is the SQL schema file.
    __table_args__ = (
        UniqueConstraint(
            "survey_version_id",
            "id",
            name="uq_survey_questions_survey_version_id_id",
        ),
    )

    survey_version: Mapped[SurveyVersion] = relationship(
        "SurveyVersion",
        foreign_keys=[survey_version_id],
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

    # Only necessary constraints live in SQLAlchemy; source of truth is the SQL schema file.

    survey_version: Mapped[SurveyVersion] = relationship("SurveyVersion", foreign_keys=[survey_version_id])
