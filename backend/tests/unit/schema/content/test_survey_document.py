"""Unit tests for the one canonical, complete survey definition schema."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from app.schema.api import limits
from app.schema.api.content.survey_document import (
    ChoiceSetValidation,
    DateValidation,
    InputBlock,
    NumberValidation,
    RatingInteraction,
    SliderInteraction,
    StringValidation,
    SurveyDefinition,
)

from .conftest import (
    block_id,
    choice_field,
    definition,
    field_id,
    input_block,
    option_id,
    section,
    section_id,
    text_field,
)


class TestBaseConfig:
    def test_unknown_property_is_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            SurveyDefinition.model_validate({"documnet": {}})

        assert "extra_forbidden" in {error["type"] for error in exc_info.value.errors()}

    @pytest.mark.parametrize(
        "payload",
        [
            {"schema_version": "1"},
            {"document": {"sections": [{"id": section_id("a"), "title": 5}]}},
        ],
    )
    def test_coercion_is_rejected(self, payload: dict[str, Any]) -> None:
        with pytest.raises(ValidationError):
            SurveyDefinition.model_validate(payload)

    def test_strip_whitespace_still_applies_under_strict(self) -> None:
        parsed = SurveyDefinition.model_validate(
            {
                "document": {
                    "sections": [
                        {
                            "id": section_id("a"),
                            "title": "  Hi  ",
                            "blocks": [{"id": block_id("divider"), "type": "divider"}],
                        }
                    ]
                }
            }
        )

        assert parsed.document.sections[0].title == "Hi"

    def test_schema_version_defaults_and_is_pinned(self) -> None:
        assert SurveyDefinition.model_validate(definition()).schema_version == 1

        with pytest.raises(ValidationError):
            SurveyDefinition.model_validate({"schema_version": 2})

    def test_lifecycle_metadata_is_not_part_of_the_definition(self) -> None:
        # Title, status and identity live on the version row, not in the portable JSON.
        for key in ("title", "status", "id", "version_id"):
            with pytest.raises(ValidationError):
                SurveyDefinition.model_validate({key: "x"})


class TestSelfContradictionIsRejected:
    """An object that contradicts itself needs no other object to be wrong."""

    def test_rating_min_above_max(self) -> None:
        with pytest.raises(ValidationError, match="rating min must be below max"):
            RatingInteraction(kind="rating", min=20, max=2)

    def test_slider_min_above_max(self) -> None:
        with pytest.raises(ValidationError, match="slider min must be below max"):
            SliderInteraction(kind="slider", min=10, max=5)

    @pytest.mark.parametrize("step", [0, -1])
    def test_non_positive_slider_step(self, step: int) -> None:
        with pytest.raises(ValidationError):
            SliderInteraction(kind="slider", step=step)

    def test_slider_step_wider_than_range(self) -> None:
        with pytest.raises(ValidationError, match="step must fit"):
            SliderInteraction(kind="slider", min=0, max=5, step=50)

    def test_inverted_text_length(self) -> None:
        with pytest.raises(ValidationError):
            StringValidation(min_length=100, max_length=5)

    def test_inverted_numeric_bounds(self) -> None:
        with pytest.raises(ValidationError):
            NumberValidation(min=10, max=5)

    def test_inverted_date_bounds(self) -> None:
        with pytest.raises(ValidationError):
            DateValidation(earliest="2026-12-31", latest="2026-01-01")  # type: ignore[arg-type]

    def test_inverted_selection_bounds(self) -> None:
        with pytest.raises(ValidationError):
            ChoiceSetValidation(min_selections=5, max_selections=2)

    def test_coherent_bounds_are_accepted(self) -> None:
        assert RatingInteraction(kind="rating", min=1, max=5).max == 5
        assert SliderInteraction(kind="slider", min=0, max=10, step=0.5).step == 0.5
        assert NumberValidation(min=0, max=10).max == 10


class TestCompletenessIsRequired:
    @pytest.mark.parametrize(
        "payload",
        [
            {},
            {"document": {"sections": []}},
            {"document": {"sections": [{"id": section_id("a"), "title": "A", "blocks": []}]}},
        ],
    )
    def test_empty_document_structure_is_rejected(self, payload: dict[str, Any]) -> None:
        with pytest.raises(ValidationError):
            SurveyDefinition.model_validate(payload)

    @pytest.mark.parametrize("field_name", ["title", "prompt"])
    def test_required_author_content_is_rejected(self, field_name: str) -> None:
        payload = definition([section("a", [input_block("b1", text_field("q1"))])])
        if field_name == "title":
            payload["document"]["sections"][0]["title"] = ""
        else:
            payload["document"]["sections"][0]["blocks"][0]["field"]["prompt"] = ""

        with pytest.raises(ValidationError):
            SurveyDefinition.model_validate(payload)

    def test_choice_question_requires_options(self) -> None:
        with pytest.raises(ValidationError):
            SurveyDefinition.model_validate(definition([section("a", [input_block("b1", choice_field("q1", []))])]))

    def test_choice_option_labels_and_local_ids_are_validated(self) -> None:
        payload = choice_field("q1", ["yes", "no"])
        payload["interaction"]["options"][1]["id"] = payload["interaction"]["options"][0]["id"]
        payload["interaction"]["options"][1]["label"] = ""

        with pytest.raises(ValidationError):
            SurveyDefinition.model_validate(definition([section("a", [input_block("b1", payload)])]))

    def test_duplicate_identifiers_parse(self) -> None:
        duplicate = input_block("b1", text_field("q1"))
        parsed = SurveyDefinition.model_validate(definition([section("a", [duplicate, dict(duplicate)])]))

        blocks = parsed.document.sections[0].blocks
        assert blocks[0].id == blocks[1].id

    def test_unresolved_condition_reference_parses(self) -> None:
        field = text_field(
            "q1",
            behaviour={
                "visibility": {
                    "mode": "conditional",
                    "condition": {
                        "field_id": field_id("nope"),
                        "operator": "equals",
                        "value": "x",
                    },
                }
            },
        )

        parsed = SurveyDefinition.model_validate(definition([section("a", [input_block("b1", field)])]))

        block = parsed.document.sections[0].blocks[0]
        assert isinstance(block, InputBlock)
        assert block.field.behaviour.visibility.mode == "conditional"

    def test_interaction_and_response_mismatch_is_rejected(self) -> None:
        field = text_field("q1", interaction={"kind": "single_choice"}, response={"type": "integer"})
        field["interaction"]["options"] = [{"id": option_id("yes"), "label": "Yes"}]

        with pytest.raises(ValidationError, match="single_choice interaction requires"):
            SurveyDefinition.model_validate(definition([section("a", [input_block("b1", field)])]))

    def test_selection_limit_cannot_exceed_options(self) -> None:
        field = choice_field("q1", ["yes", "no"])
        field["interaction"]["kind"] = "multiple_choice"
        field["response"] = {
            "type": "choice_set",
            "validation": {"max_selections": 3},
        }

        with pytest.raises(ValidationError, match="number of options"):
            SurveyDefinition.model_validate(definition([section("a", [input_block("b1", field)])]))

    def test_condition_operator_value_relationship_is_local(self) -> None:
        field = text_field(
            "q1",
            behaviour={
                "visibility": {
                    "mode": "conditional",
                    "condition": {
                        "field_id": field_id("source"),
                        "operator": "is_answered",
                        "value": "unexpected",
                    },
                }
            },
        )

        with pytest.raises(ValidationError, match="does not accept a value"):
            SurveyDefinition.model_validate(definition([section("a", [input_block("b1", field)])]))


class TestDiscriminators:
    @pytest.mark.parametrize(
        ("interaction", "response"),
        [
            ({"kind": "text"}, {"type": "string"}),
            ({"kind": "long_text"}, {"type": "string"}),
            ({"kind": "number"}, {"type": "decimal"}),
            (
                {
                    "kind": "single_choice",
                    "options": [{"id": option_id("yes"), "label": "Yes"}],
                },
                {"type": "choice"},
            ),
            (
                {
                    "kind": "multiple_choice",
                    "options": [{"id": option_id("yes"), "label": "Yes"}],
                },
                {"type": "choice_set"},
            ),
            ({"kind": "rating"}, {"type": "integer"}),
            ({"kind": "slider"}, {"type": "decimal"}),
            ({"kind": "date"}, {"type": "date"}),
        ],
    )
    def test_interaction_kinds_parse(
        self,
        interaction: dict[str, Any],
        response: dict[str, Any],
    ) -> None:
        field = text_field("q1", interaction=interaction, response=response)

        SurveyDefinition.model_validate(definition([section("a", [input_block("b1", field)])]))

    @pytest.mark.parametrize("block_type", ["heading", "paragraph", "notice", "divider", "image"])
    def test_block_types_parse(self, block_type: str) -> None:
        blocks: dict[str, dict[str, Any]] = {
            "heading": {"content": {"text": "Heading"}},
            "paragraph": {"content": {"text": "Paragraph"}},
            "notice": {"content": {"title": "Notice", "text": "Text"}},
            "divider": {},
            "image": {"content": {"url": "https://example.test/image.png", "alt_text": "Image"}},
        }
        parsed = SurveyDefinition.model_validate(
            definition(
                [
                    section(
                        "a",
                        [{"id": block_id("b1"), "type": block_type, **blocks[block_type]}],
                    )
                ]
            )
        )

        assert parsed.document.sections[0].blocks[0].type == block_type

    def test_unknown_block_type_is_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            SurveyDefinition.model_validate(definition([section("a", [{"id": block_id("b1"), "type": "video"}])]))

        assert exc_info.value.errors()[0]["type"] == "union_tag_invalid"

    def test_unknown_interaction_kind_is_rejected(self) -> None:
        field = text_field("q1", interaction={"kind": "carousel"})

        with pytest.raises(ValidationError):
            SurveyDefinition.model_validate(definition([section("a", [input_block("b1", field)])]))

    def test_divider_does_not_accept_content(self) -> None:
        with pytest.raises(ValidationError):
            SurveyDefinition.model_validate(
                definition([section("a", [{"id": block_id("b1"), "type": "divider", "content": {}}])])
            )


class TestIdentifiers:
    @pytest.mark.parametrize(
        "identifier",
        ["section_", "section-hyphen", "SECTION_UPPER", "section_bad!"],
    )
    def test_malformed_section_id_is_rejected(self, identifier: str) -> None:
        with pytest.raises(ValidationError):
            SurveyDefinition.model_validate({"document": {"sections": [{"id": identifier}]}})

    def test_wrong_prefix_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SurveyDefinition.model_validate({"document": {"sections": [{"id": block_id("a")}]}})

    @pytest.mark.parametrize("key", ["", "Smoking", "smoking-status", "x" * 65])
    def test_malformed_field_key_is_rejected(self, key: str) -> None:
        field = text_field("q1", key=key)

        with pytest.raises(ValidationError):
            SurveyDefinition.model_validate(definition([section("a", [input_block("b1", field)])]))


class TestBounds:
    def test_section_limit(self) -> None:
        sections = [{"id": section_id(f"s{i}")} for i in range(limits.SECTIONS_MAX + 1)]

        with pytest.raises(ValidationError):
            SurveyDefinition.model_validate({"document": {"sections": sections}})

    def test_blocks_per_section_limit(self) -> None:
        blocks = [{"id": block_id(f"b{i}"), "type": "divider"} for i in range(limits.BLOCKS_PER_SECTION_MAX + 1)]

        with pytest.raises(ValidationError):
            SurveyDefinition.model_validate(definition([section("a", blocks)]))

    def test_definition_byte_size_limit(self) -> None:
        # One whole-document ceiling, so no per-property traversal has to be maintained.
        chunk = "x" * limits.LONG_TEXT_MAX
        blocks = [
            {"id": block_id(f"b{i}"), "type": "paragraph", "content": {"text": chunk}}
            for i in range(limits.BLOCKS_PER_SECTION_MAX)
        ]
        sections = [section(f"s{i}", blocks) for i in range(60)]

        with pytest.raises(ValidationError, match="exceeds the maximum allowed size"):
            SurveyDefinition.model_validate({"document": {"sections": sections}})

    def test_non_finite_numbers_are_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SliderInteraction.model_validate_json('{"kind": "slider", "min": NaN}')

    def test_bool_is_not_accepted_as_a_number(self) -> None:
        with pytest.raises(ValidationError):
            SliderInteraction(kind="slider", min=True)  # type: ignore[arg-type]

    def test_image_url_scheme_is_restricted(self) -> None:
        for url in ("javascript:alert(1)", "file:///etc/passwd", "http://example.test/a.png"):
            with pytest.raises(ValidationError):
                SurveyDefinition.model_validate(
                    definition(
                        [
                            section(
                                "a",
                                [{"id": block_id("b1"), "type": "image", "content": {"url": url}}],
                            )
                        ]
                    )
                )


class TestRoundTrip:
    def test_definition_round_trips(self) -> None:
        payload = definition(
            [
                section("intro", [{"id": block_id("h"), "type": "heading", "content": {"text": "Hi"}}]),
                section("health", [input_block("b1", choice_field("q1", ["yes", "no"]))]),
            ]
        )

        parsed = SurveyDefinition.model_validate(payload)

        assert SurveyDefinition.model_validate(parsed.model_dump(mode="json")) == parsed

    def test_serialisation_is_snake_case(self) -> None:
        field = text_field("q1", help_text="Some help")
        parsed = SurveyDefinition.model_validate(definition([section("a", [input_block("b1", field)])]))

        dumped = parsed.model_dump(mode="json")
        assert "help_text" in dumped["document"]["sections"][0]["blocks"][0]["field"]

    def test_camel_case_input_and_output_aliases(self) -> None:
        payload = definition([section("intro", [input_block("b1", text_field("q1"))])])
        survey_field = payload["document"]["sections"][0]["blocks"][0]["field"]
        survey_field["helpText"] = "Some help"

        parsed = SurveyDefinition.model_validate(payload)

        assert (
            parsed.model_dump(mode="json", by_alias=True)["document"]["sections"][0]["blocks"][0]["field"]["helpText"]
            == "Some help"
        )

    def test_list_order_is_preserved(self) -> None:
        parsed = SurveyDefinition.model_validate(
            definition(
                [
                    section("a", [input_block("b1", text_field("q1"))]),
                    section("b", [input_block("b2", text_field("q2"))]),
                ]
            )
        )

        assert [s.id for s in parsed.document.sections] == [section_id("a"), section_id("b")]
