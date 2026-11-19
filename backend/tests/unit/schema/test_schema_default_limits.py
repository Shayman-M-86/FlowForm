"""Category limits and their deliberate field-specific exceptions."""

import pytest
from pydantic import Field, TypeAdapter, ValidationError

from app.schema.api.requests.ai_import import AIImportRequest
from app.schema.models.common.base import DataModel
from app.schema.models.survey_document.answers import AnsweredAnswer
from app.schema.models.survey_document.document import SurveySection, TextContent
from app.schema.types import LimitedDict, LimitedList, LongString, ShortString


class Example(DataModel):
    ordinary: str
    short: ShortString
    long: LongString
    items: LimitedList[int]
    mapping: LimitedDict[int]


def example():
    return {
        "ordinary": "x" * 2000,
        "short": "x" * 128,
        "long": "x" * 10000,
        "items": list(range(100)),
        "mapping": {str(i): i for i in range(100)},
    }


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("ordinary", "x" * 2001),
        ("short", "x" * 129),
        ("long", "x" * 10001),
        ("items", list(range(101))),
        ("mapping", {str(i): i for i in range(101)}),
    ],
)
def test_category_boundaries(name, value):
    Example.model_validate(example())
    with pytest.raises(ValidationError):
        Example.model_validate(example() | {name: value})


def test_defaults_preserve_whitespace():
    assert Example.model_validate(example() | {"ordinary": "  text  "}).ordinary == "  text  "


def test_explicit_larger_limits_override_defaults():
    class Larger(DataModel):
        values: LimitedList[int] = Field(max_length=200)

    Larger(values=list(range(200)))
    with pytest.raises(ValidationError):
        Larger(values=list(range(201)))
    AIImportRequest(prompt="x" * 4000)
    with pytest.raises(ValidationError):
        AIImportRequest(prompt="x" * 4001)


def test_nested_long_content_and_survey_block_exception():
    TextContent(text="x" * 10000)
    with pytest.raises(ValidationError):
        TextContent(text="x" * 10001)
    SurveySection(id="section", title="Section", blocks=[{"id": str(i), "type": "divider"} for i in range(1000)])
    with pytest.raises(ValidationError):
        SurveySection(id="section", title="Section", blocks=[{"id": str(i), "type": "divider"} for i in range(1001)])


def test_long_answer_limit_and_submitted_constraints_both_apply():
    raw = {"state": "answered", "answer_spec": {"type": "string", "required": True}}
    AnsweredAnswer.model_validate(raw | {"answer_value": "x" * 10000})
    with pytest.raises(ValidationError):
        AnsweredAnswer.model_validate(raw | {"answer_value": "x" * 10001})
    with pytest.raises(ValidationError):
        AnsweredAnswer.model_validate(
            raw
            | {
                "answer_value": "long",
                "answer_spec": {
                    "type": "string",
                    "required": True,
                    "constraints": {"maxLength": 3},
                },
            }
        )


def test_collection_constraints_are_exported():
    assert TypeAdapter(LimitedList[int]).json_schema()["maxItems"] == 100
    assert TypeAdapter(LimitedDict[int]).json_schema()["maxProperties"] == 100
    assert TypeAdapter(LongString).json_schema()["maxLength"] == 10000
