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
    UniqueConstraint(
        "survey_version_id",
        "question_key",
        name="uq_survey_questions_survey_version_id_question_key",
    ),
    CheckConstraint(
        "jsonb_typeof(question_schema) = 'object'",
        name="ck_survey_questions_question_schema_is_object",
    ),
    CheckConstraint(
        "jsonb_has_exact_keys(question_schema, ARRAY['family', 'label', 'schema', 'ui'])",
        name="ck_survey_questions_question_schema_top_level_shape_valid",
    ),
    CheckConstraint(
        "question_schema->>'family' IN ('choice', 'field', 'matching', 'rating')",
        name="ck_survey_questions_question_family_valid",
    ),
    CheckConstraint(
        "jsonb_typeof(question_schema->'label') = 'string'"
        " AND btrim(question_schema->>'label') <> ''",
        name="ck_survey_questions_question_label_valid",
    ),
    CheckConstraint(
        "jsonb_typeof(question_schema->'schema') = 'object'",
        name="ck_survey_questions_question_schema_inner_is_object",
    ),
    CheckConstraint(
        "jsonb_typeof(question_schema->'ui') = 'object'",
        name="ck_survey_questions_question_ui_is_object",
    ),
    CheckConstraint(
        "question_schema->>'family' <> 'choice'"
        " OR (jsonb_has_exact_keys(question_schema->'schema', ARRAY['options', 'min_selected', 'max_selected'])"
        " AND jsonb_typeof(question_schema->'schema'->'options') = 'array'"
        " AND jsonb_typeof(question_schema->'schema'->'min_selected') = 'number'"
        " AND jsonb_typeof(question_schema->'schema'->'max_selected') = 'number')",
        name="ck_survey_questions_question_choice_schema_valid",
    ),
    CheckConstraint(
        "question_schema->>'family' <> 'field'"
        " OR (jsonb_has_exact_keys(question_schema->'schema', ARRAY['field_type'])"
        " AND question_schema->'schema'->>'field_type' IN ('text', 'email', 'number', 'date', 'phone'))",
        name="ck_survey_questions_question_field_schema_valid",
    ),
    CheckConstraint(
        "question_schema->>'family' <> 'matching'"
        " OR (jsonb_has_exact_keys(question_schema->'schema', ARRAY['left_items', 'right_items'])"
        " AND jsonb_typeof(question_schema->'schema'->'left_items') = 'array'"
        " AND jsonb_typeof(question_schema->'schema'->'right_items') = 'array')",
        name="ck_survey_questions_question_matching_schema_valid",
    ),
    CheckConstraint(
        "question_schema->>'family' <> 'rating'"
        " OR (jsonb_has_exact_keys(question_schema->'schema', ARRAY['min', 'max'])"
        " AND jsonb_typeof(question_schema->'schema'->'min') = 'number'"
        " AND jsonb_typeof(question_schema->'schema'->'max') = 'number'"
        " AND (question_schema->'schema'->>'max')::numeric > (question_schema->'schema'->>'min')::numeric)",
        name="ck_survey_questions_question_rating_schema_valid",
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
    UniqueConstraint(
        "survey_version_id",
        "rule_key",
        name="uq_survey_rules_survey_version_id_rule_key",
    ),
    CheckConstraint(
        "jsonb_typeof(rule_schema) = 'object'",
        name="ck_survey_rules_rule_schema_is_object",
    ),
    CheckConstraint(
        "jsonb_has_exact_keys(rule_schema, ARRAY['target', 'condition', 'effects'])"
        " OR jsonb_has_exact_keys(rule_schema, ARRAY['target', 'sort_order', 'condition', 'effects'])",
        name="ck_survey_rules_rule_schema_top_level_shape_valid",
    ),
    CheckConstraint(
        "jsonb_typeof(rule_schema->'target') = 'string'"
        " AND btrim(rule_schema->>'target') <> ''",
        name="ck_survey_rules_rule_target_valid",
    ),
    CheckConstraint(
        "rule_schema->'condition' IS NOT NULL"
        " AND jsonb_typeof(rule_schema->'condition') = 'object'",
        name="ck_survey_rules_rule_condition_is_object",
    ),
    CheckConstraint(
        "rule_schema->'effects' IS NOT NULL"
        " AND jsonb_typeof(rule_schema->'effects') = 'object'",
        name="ck_survey_rules_rule_effects_is_object",
    ),
    CheckConstraint(
        "(rule_schema ? 'sort_order') = FALSE"
        " OR jsonb_typeof(rule_schema->'sort_order') = 'number'",
        name="ck_survey_rules_rule_sort_order_valid",
    ),
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
        "jsonb_typeof(scoring_schema->'target') = 'string'"
        " AND btrim(scoring_schema->>'target') <> ''",
        name="ck_survey_scoring_rules_scoring_target_valid",
    ),
    CheckConstraint(
        "jsonb_typeof(scoring_schema->'bucket') = 'string'"
        " AND btrim(scoring_schema->>'bucket') <> ''",
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
        "(scoring_schema ? 'condition') = FALSE"
        " OR jsonb_typeof(scoring_schema->'condition') = 'object'",
        name="ck_survey_scoring_rules_scoring_condition_is_object",
    ),
)

    survey_version: Mapped[SurveyVersion] = relationship(
        "SurveyVersion", foreign_keys=[survey_version_id]
    )
