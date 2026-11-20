"""Resource limits must guard inputs without rejecting complete output data."""

from datetime import UTC, datetime

import pytest
from pydantic import TypeAdapter, ValidationError
from werkzeug.routing import Map
from werkzeug.routing import ValidationError as RoutingValidationError

from app.middleware.url_converters import BoundedIntegerConverter
from app.schema.api.common.types import PageItems, ProjectPermission, ProjectPermissionSet
from app.schema.api.responses.survey_results import SurveySessionTreeResponses
from app.schema.types import DatabaseIdentity, LimitedList, PageSize


def test_url_ids_and_shared_ids_have_the_same_storage_range():
    converter = BoundedIntegerConverter(Map())
    adapter = TypeAdapter(DatabaseIdentity)
    for value in [1, 2**31, 2**63 - 1]:
        assert converter.to_python(str(value)) == adapter.validate_python(value)
    for value in [0, -1, 2**63]:
        with pytest.raises(RoutingValidationError):
            converter.to_python(str(value))
        with pytest.raises(ValidationError):
            adapter.validate_python(value)


def test_input_and_page_limits_are_preserved():
    TypeAdapter(LimitedList[int]).validate_python(list(range(100)))
    TypeAdapter(PageItems[int]).validate_python(list(range(100)))
    for alias in [LimitedList[int], PageItems[int]]:
        with pytest.raises(ValidationError):
            TypeAdapter(alias).validate_python(list(range(101)))
    assert TypeAdapter(PageSize).validate_python(100) == 100
    with pytest.raises(ValidationError):
        TypeAdapter(PageSize).validate_python(101)


def test_complete_session_results_are_not_capped_at_fifty_or_one_hundred():
    now = datetime(2020, 1, 1, tzinfo=UTC)
    result = SurveySessionTreeResponses.model_validate(
        {
            "session": {
                "id": "10000000-0000-4000-8000-000000000001",
                "survey_id": 1,
                "survey_version_id": 1,
                "session_status": "in_progress",
                "started_at": now,
                "last_activity_at": now,
            },
            "answers": [
                {"field_uuid": f"10000000-0000-4000-8000-{i:012d}", "has_encrypted_answer": False, "decrypted": False}
                for i in range(201)
            ],
            "events": [{"event_type": "field_viewed", "received_at": now} for _ in range(201)],
        }
    )
    assert len(result.answers) == 201
    assert result.events is not None
    assert len(result.events) == 201


def test_permission_membership_is_authoritative_without_a_redundant_length_cap():
    from typing import get_args

    values = get_args(ProjectPermission)
    adapter = TypeAdapter(ProjectPermissionSet)
    assert adapter.validate_python(list(values) * 20) == set(values)
    assert adapter.json_schema()["uniqueItems"] is True
    assert "maxItems" not in adapter.json_schema()
    with pytest.raises(ValidationError):
        adapter.validate_python(["unknown:permission"])
