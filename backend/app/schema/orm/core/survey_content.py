from typing import TYPE_CHECKING, Literal

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
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

    `question_key` is the stable node id:
    - question node: "q1", "q2", etc.
    - rule node: "r1", "r2", etc.
    """

    __tablename__ = "survey_questions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    survey_version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("survey_versions.id", ondelete="CASCADE"),
        nullable=False,
    )

    question_key: Mapped[str] = mapped_column(Text, nullable=False)
    sort_key: Mapped[int] = mapped_column(Integer, nullable=False)
    node_type: Mapped[SurveyNodeType] = mapped_column(Text, nullable=False)
    question_schema: Mapped[dict] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "survey_version_id",
            "question_key",
            name="uq_survey_questions_survey_version_id_question_key",
        ),
        UniqueConstraint(
            "survey_version_id",
            "sort_key",
            name="uq_survey_questions_survey_version_id_sort_key",
        ),
        CheckConstraint(
            "node_type IN ('question', 'rule')",
            name="ck_survey_questions_node_type_valid",
        ),
        CheckConstraint(
            "sort_key > 0",
            name="ck_survey_questions_sort_key_positive",
        ),
        CheckConstraint(
            "length(question_key) BETWEEN 1 AND 128",
            name="ck_survey_questions_question_key_len",
        ),
        CheckConstraint(
            "question_key ~ '^[A-Za-z0-9_-]+$'",
            name="ck_survey_questions_question_key_format",
        ),
        CheckConstraint(
            "length(question_schema::text) <= 10000",
            name="ck_survey_questions_schema_size",
        ),
        CheckConstraint(
            "node_type <> 'question' OR jsonb_typeof(question_schema) = 'object'",
            name="ck_survey_questions_question_schema_is_object",
        ),
        CheckConstraint(
            "node_type <> 'question' OR question_schema->>'family' IN ('choice', 'field', 'matching', 'rating')",
            name="ck_survey_questions_question_family_valid",
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

    __table_args__ = (
        UniqueConstraint(
            "survey_version_id",
            "scoring_key",
            name="uq_survey_scoring_rules_survey_version_id_scoring_key",
        ),
        CheckConstraint(
            "jsonb_typeof(scoring_schema) = 'object'",
            name="ck_survey_scoring_rules_scoring_schema_is_object",
        ),
        CheckConstraint(
            "scoring_schema ?& ARRAY['target', 'bucket', 'strategy', 'config']",
            name="ck_survey_scoring_rules_scoring_schema_required_keys_present",
        ),
        CheckConstraint(
            "jsonb_typeof(scoring_schema->'target') = 'string' AND btrim(scoring_schema->>'target') <> ''",
            name="ck_survey_scoring_rules_scoring_target_valid",
        ),
        CheckConstraint(
            "jsonb_typeof(scoring_schema->'bucket') = 'string' AND btrim(scoring_schema->>'bucket') <> ''",
            name="ck_survey_scoring_rules_scoring_bucket_valid",
        ),
        CheckConstraint(
            "scoring_schema->>'strategy' IN ("
            "'choice_option_map', "
            "'matching_answer_key', "
            "'rating_direct', "
            "'field_numeric_ranges'"
            ")",
            name="ck_survey_scoring_rules_scoring_strategy_valid",
        ),
        CheckConstraint(
            "jsonb_typeof(scoring_schema->'config') = 'object'",
            name="ck_survey_scoring_rules_scoring_config_is_object",
        ),
        CheckConstraint(
            "(scoring_schema ? 'condition') = FALSE OR jsonb_typeof(scoring_schema->'condition') = 'object'",
            name="ck_survey_scoring_rules_scoring_condition_is_object",
        ),
    )

    survey_version: Mapped[SurveyVersion] = relationship("SurveyVersion", foreign_keys=[survey_version_id])
