"""Every mapped model must generate a complete keyword-only constructor."""

import importlib
import inspect
from dataclasses import MISSING, fields, is_dataclass
from datetime import UTC, datetime
from types import UnionType
from typing import Annotated, Any, Literal, NewType, TypeAliasType, Union, cast, get_args, get_origin
from uuid import UUID, uuid4

import pytest
from pydantic import TypeAdapter

import app.schema.orm  # noqa: F401
from app.db.base import CoreBase, ResponseBase
from app.schema.orm.core.submission_answer_slot import SubmissionAnswerSlot
from app.schema.types import SubmissionSessionId, SurveyFieldUuid, SurveyVersionId


def mapped_models():
    return [mapper for base in (CoreBase, ResponseBase) for mapper in base.registry.mappers]


def sample(annotation):
    if isinstance(annotation, TypeAliasType):
        return sample(annotation.__value__)
    if isinstance(annotation, NewType):
        return sample(annotation.__supertype__)
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is Annotated:
        return sample(args[0])
    if origin is Literal:
        return args[0]
    if origin in (Union, UnionType):
        return sample(next(a for a in args if a is not type(None)))
    return {
        int: 1,
        str: "value",
        bool: False,
        bytes: b"value",
        UUID: uuid4(),
        datetime: datetime.now(UTC),
        dict: {},
    }.get(annotation)


@pytest.mark.parametrize("mapper", mapped_models(), ids=lambda m: m.class_.__name__)
def test_constructor_covers_mapped_fields_without_catch_all(mapper):
    model = mapper.class_
    assert "__init__" in model.__dict__
    signature = inspect.signature(model.__init__)
    params = {name: p for name, p in signature.parameters.items() if name != "self"}
    assert is_dataclass(model)
    dataclass_fields = {field.name: field for field in fields(model)}
    assert set(dataclass_fields) == set(mapper.attrs.keys())
    assert set(params) == {name for name, field in dataclass_fields.items() if field.init}
    relationship_names = set(mapper.relationships.keys())
    assert all(not dataclass_fields[name].init for name in relationship_names)
    for column in mapper.columns:
        generated_identity = column.key == "id" and (
            column.server_default is not None
            or column.identity is not None
            or column is mapper.local_table.autoincrement_column
        )
        if generated_identity:
            assert column.key not in params
    assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in params.values())
    namespace = vars(importlib.import_module(model.__module__)) | {m.class_.__name__: m.class_ for m in mapped_models()}
    kwargs = {}
    for name, parameter in params.items():
        if parameter.default is inspect.Parameter.empty:
            annotation = parameter.annotation
            if isinstance(annotation, str):
                annotation = eval(annotation, namespace)
            kwargs[name] = sample(annotation)
        else:
            field = dataclass_fields[name]
            if field.default_factory is MISSING:
                assert parameter.default == field.default
            else:
                assert parameter.default is not inspect.Parameter.empty
    instance = model(**kwargs)
    assert isinstance(instance, model)
    with pytest.raises(TypeError, match="unexpected keyword"):
        model(**kwargs, unknown_property="typo")


def test_answer_slot_rejects_legacy_constructor_names():
    with pytest.raises(TypeError, match="unexpected keyword"):
        cast(Any, SubmissionAnswerSlot)(
            submission_session_id=uuid4(), survey_version_id=1, question_node_id=uuid4(), question_key="q1"
        )


def test_generated_id_can_be_omitted_and_is_not_a_constructor_input():
    slot = SubmissionAnswerSlot(
        submission_session_id=TypeAdapter(SubmissionSessionId).validate_python(uuid4()),
        survey_version_id=TypeAdapter(SurveyVersionId).validate_python(1),
        field_uuid=TypeAdapter(SurveyFieldUuid).validate_python(uuid4()),
    )
    assert slot.id is None
    with pytest.raises(TypeError, match="unexpected keyword"):
        cast(Any, SubmissionAnswerSlot)(
            id=uuid4(), submission_session_id=uuid4(), survey_version_id=1, field_uuid=uuid4()
        )


def test_session_operation_timestamps_preserve_explicit_values():
    from datetime import timedelta

    from app.schema.orm.core.submission_session import SubmissionSession

    timestamp = datetime(2020, 1, 1, tzinfo=UTC)
    common = {
        "project_id": 1,
        "survey_id": 1,
        "survey_version_id": 1,
        "response_store_id": 1,
        "browser_session_token_hash": b"token-hash",
        "linkage_key_version": 1,
        "expires_at": timestamp + timedelta(days=1),
    }
    explicit = SubmissionSession(**common, started_at=timestamp, last_activity_at=timestamp)
    assert explicit.started_at == timestamp and explicit.last_activity_at == timestamp
    defaulted = SubmissionSession(**common)
    assert defaulted.started_at.tzinfo is UTC and defaulted.last_activity_at.tzinfo is UTC
