"""Small document-wide publication validator for canonical survey definitions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from app.domain.errors import SurveyPublishError
from app.domain.surveys.publication.issues import (
    CONDITION_DEPENDENCY_CYCLE,
    CONDITION_FIELD_MISSING,
    CONDITION_OPERATOR_INCOMPATIBLE,
    CONDITION_OPTION_MISSING,
    CONDITION_SELF_REFERENCE,
    CONDITION_VALUE_TYPE_INVALID,
    DUPLICATE_BLOCK_ID,
    DUPLICATE_FIELD_ID,
    DUPLICATE_FIELD_KEY,
    DUPLICATE_SECTION_ID,
    PublicationIssue,
    PublicationIssueCode,
)
from app.schema.api.content.survey_document import (
    ConditionalVisibility,
    InputBlock,
    MultipleChoiceInteraction,
    SingleChoiceInteraction,
    SurveyBlock,
    SurveyDefinition,
    SurveyField,
    SurveySection,
)
from app.schema.enums import (
    SURVEY_PRESENCE_OPERATORS,
    SurveyConditionOperator,
    SurveyResponseType,
)

ChoiceInteraction = SingleChoiceInteraction | MultipleChoiceInteraction

_OPERATORS_BY_RESPONSE: dict[SurveyResponseType, frozenset[SurveyConditionOperator]] = {
    "string": frozenset({"equals", "not_equals", "contains", "is_answered", "is_empty"}),
    "integer": frozenset({"equals", "not_equals", "greater_than", "less_than", "is_answered", "is_empty"}),
    "decimal": frozenset({"equals", "not_equals", "greater_than", "less_than", "is_answered", "is_empty"}),
    "date": frozenset({"equals", "not_equals", "greater_than", "less_than", "is_answered", "is_empty"}),
    "choice": frozenset({"equals", "not_equals", "is_answered", "is_empty"}),
    "choice_set": frozenset({"equals", "not_equals", "contains", "is_answered", "is_empty"}),
}


@dataclass(slots=True)
class PublicationIndex:
    """Lookups built in one traversal; lists retain duplicate occurrences."""

    sections_by_id: dict[str, list[SurveySection]] = field(default_factory=dict)
    blocks_by_id: dict[str, list[SurveyBlock]] = field(default_factory=dict)
    fields_by_id: dict[str, list[SurveyField]] = field(default_factory=dict)
    fields_by_key: dict[str, list[SurveyField]] = field(default_factory=dict)
    options_by_field_id: dict[str, set[str]] = field(default_factory=dict)
    fields_in_order: tuple[SurveyField, ...] = ()
    conditional_fields: tuple[tuple[SurveyField, ConditionalVisibility], ...] = ()

    @classmethod
    def build(cls, definition: SurveyDefinition) -> PublicationIndex:
        index = cls()
        fields_in_order: list[SurveyField] = []
        conditional_fields: list[tuple[SurveyField, ConditionalVisibility]] = []

        for section in definition.document.sections:
            index.sections_by_id.setdefault(section.id, []).append(section)
            for block in section.blocks:
                index.blocks_by_id.setdefault(block.id, []).append(block)
                if not isinstance(block, InputBlock):
                    continue
                survey_field = block.field
                fields_in_order.append(survey_field)
                index.fields_by_id.setdefault(survey_field.id, []).append(survey_field)
                index.fields_by_key.setdefault(survey_field.key, []).append(survey_field)

                visibility = survey_field.behaviour.visibility
                if isinstance(visibility, ConditionalVisibility):
                    conditional_fields.append((survey_field, visibility))

                interaction = survey_field.interaction
                if isinstance(interaction, ChoiceInteraction):
                    index.options_by_field_id.setdefault(survey_field.id, set()).update(
                        option.id for option in interaction.options
                    )

        index.fields_in_order = tuple(fields_in_order)
        index.conditional_fields = tuple(conditional_fields)
        return index


def validate_for_publication(definition: SurveyDefinition) -> list[PublicationIssue]:
    """Return every document-wide logical issue in deterministic document order."""
    index = PublicationIndex.build(definition)
    return [
        *validate_unique_identifiers(index),
        *validate_field_references(index),
        *validate_dependency_cycles(index),
    ]


def ensure_publishable(definition: SurveyDefinition) -> None:
    """Raise a domain error containing every issue when publication is invalid."""
    issues = validate_for_publication(definition)
    if issues:
        raise SurveyPublishError(
            "Survey definition is not ready for publication.",
            issues=issues,
        )


def validate_unique_identifiers(index: PublicationIndex) -> list[PublicationIssue]:
    """Validate identities whose uniqueness requires comparing separate objects."""
    return [
        *_duplicate_issues(DUPLICATE_SECTION_ID, "Section id", index.sections_by_id),
        *_duplicate_issues(DUPLICATE_BLOCK_ID, "Block id", index.blocks_by_id),
        *_duplicate_issues(DUPLICATE_FIELD_ID, "Field id", index.fields_by_id),
        *_duplicate_issues(DUPLICATE_FIELD_KEY, "Field key", index.fields_by_key),
    ]


def _duplicate_issues(
    code: PublicationIssueCode,
    label: str,
    occurrences_by_value: Mapping[str, Sequence[object]],
) -> list[PublicationIssue]:
    return [
        PublicationIssue(
            code=code,
            message=f"{label} {value!r} is used more than once.",
            object_id=value,
        )
        for value, occurrences in occurrences_by_value.items()
        if len(occurrences) > 1
    ]


def validate_field_references(index: PublicationIndex) -> list[PublicationIssue]:
    """Validate conditional visibility against referenced fields and their contracts."""
    found: list[PublicationIssue] = []
    for survey_field, visibility in index.conditional_fields:
        issue = _validate_field_condition(survey_field, visibility, index)
        if issue is not None:
            found.append(issue)
    return found


def _validate_field_condition(
    survey_field: SurveyField,
    visibility: ConditionalVisibility,
    index: PublicationIndex,
) -> PublicationIssue | None:
    condition = visibility.condition
    sources = index.fields_by_id.get(condition.field_id, ())

    if not sources:
        return _field_issue(
            CONDITION_FIELD_MISSING,
            f"Referenced field {condition.field_id!r} does not exist.",
            survey_field,
        )
    if condition.field_id == survey_field.id:
        return _field_issue(
            CONDITION_SELF_REFERENCE,
            "A field cannot depend on its own answer.",
            survey_field,
        )
    if len(sources) > 1:
        return None

    source = sources[0]
    response_type = source.response.type
    if condition.operator not in _OPERATORS_BY_RESPONSE[response_type]:
        return _field_issue(
            CONDITION_OPERATOR_INCOMPATIBLE,
            f"Operator {condition.operator!r} cannot be applied to a {response_type} response.",
            survey_field,
        )
    if condition.operator in SURVEY_PRESENCE_OPERATORS:
        return None
    if not _value_matches_response(response_type, condition.value):
        return _field_issue(
            CONDITION_VALUE_TYPE_INVALID,
            f"Condition value does not match the {response_type} response.",
            survey_field,
        )
    if response_type in {"choice", "choice_set"} and condition.value not in index.options_by_field_id.get(
        condition.field_id, set()
    ):
        return _field_issue(
            CONDITION_OPTION_MISSING,
            f"Referenced option {condition.value!r} does not exist on the source field.",
            survey_field,
        )
    return None


def _value_matches_response(response_type: SurveyResponseType, value: object) -> bool:
    if response_type in {"integer", "decimal"}:
        return isinstance(value, int | float) and not isinstance(value, bool)
    return isinstance(value, str)


def _field_issue(
    code: PublicationIssueCode,
    message: str,
    survey_field: SurveyField,
) -> PublicationIssue:
    return PublicationIssue(code=code, message=message, object_id=survey_field.id)


def validate_dependency_cycles(index: PublicationIndex) -> list[PublicationIssue]:
    """Report each field participating in a conditional-visibility dependency cycle."""
    dependencies: dict[str, str] = {}
    for survey_field, visibility in index.conditional_fields:
        source_id = visibility.condition.field_id
        if source_id == survey_field.id:
            continue
        if len(index.fields_by_id.get(survey_field.id, ())) != 1:
            continue
        if len(index.fields_by_id.get(source_id, ())) != 1:
            continue
        dependencies[survey_field.id] = source_id

    cycle_members = _find_cycle_members(dependencies)
    return [
        PublicationIssue(
            code=CONDITION_DEPENDENCY_CYCLE,
            message="Field visibility dependencies form a cycle.",
            object_id=survey_field.id,
        )
        for survey_field in index.fields_in_order
        if survey_field.id in cycle_members
    ]


def _find_cycle_members(dependencies: Mapping[str, str]) -> set[str]:
    cycle_members: set[str] = set()
    completed: set[str] = set()
    for start in dependencies:
        if start in completed:
            continue
        path: list[str] = []
        positions: dict[str, int] = {}
        current = start
        while current in dependencies and current not in completed:
            if current in positions:
                cycle_members.update(path[positions[current] :])
                break
            positions[current] = len(path)
            path.append(current)
            current = dependencies[current]
        completed.update(path)
    return cycle_members
