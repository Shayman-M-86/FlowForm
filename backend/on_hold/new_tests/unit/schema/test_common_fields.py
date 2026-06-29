"""Unit tests for shared API schema field types."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from app.schema.api import limits
from app.schema.api.common.fields import (
    AccountEmail,
    FutureExpiresAt,
    NormalisedEmail,
    PublicLinkToken,
    SchemaIdStr,
    Slug,
)
from app.schema.api.requests.survey_responses import ListSurveyResponsesRequest


def test_normalised_email_strips_and_lowercases() -> None:
    """Shared normalized email fields should trim and lowercase input."""
    adapter = TypeAdapter(NormalisedEmail)

    assert str(adapter.validate_python("  USER@Example.COM  ")) == "user@example.com"


def test_account_email_strips_and_lowercases() -> None:
    """Account email fields should use the same visible normalization policy."""
    adapter = TypeAdapter(AccountEmail)

    assert adapter.validate_python("  USER@Example.COM  ") == "user@example.com"


def test_invalid_email_rejected() -> None:
    """Shared email fields should reject invalid email strings."""
    adapter = TypeAdapter(NormalisedEmail)

    with pytest.raises(ValidationError):
        adapter.validate_python("not-an-email")


@pytest.mark.parametrize("value", ["customer-intake", "survey-2026", "a"])
def test_slug_accepts_canonical_values(value: str) -> None:
    """Slug fields should accept lowercase dash-separated values."""
    adapter = TypeAdapter(Slug)

    assert adapter.validate_python(value) == value


@pytest.mark.parametrize("value", ["Customer Intake", "customer_intake", "-bad", "bad-"])
def test_slug_rejects_noncanonical_values(value: str) -> None:
    """Slug fields should reject spaces, underscores, and edge dashes."""
    adapter = TypeAdapter(Slug)

    with pytest.raises(ValidationError):
        adapter.validate_python(value)


def test_public_link_token_enforces_size_limit() -> None:
    """Public link tokens should use the shared token limit."""
    adapter = TypeAdapter(PublicLinkToken)

    with pytest.raises(ValidationError):
        adapter.validate_python("x" * (limits.TOKEN_MAX + 1))


def test_schema_id_strips_whitespace() -> None:
    """Schema IDs should be normalized before use in answer payloads."""
    adapter = TypeAdapter(SchemaIdStr)

    assert adapter.validate_python("  node-1  ") == "node-1"


def test_future_expires_at_requires_aware_future_datetime() -> None:
    """Expiry fields should require timezone-aware future datetimes."""
    adapter = TypeAdapter(FutureExpiresAt)
    future = datetime.now(UTC) + timedelta(hours=1)

    assert adapter.validate_python(future) == future
    with pytest.raises(ValidationError):
        adapter.validate_python(datetime.now(UTC) - timedelta(hours=1))
    with pytest.raises(ValidationError):
        adapter.validate_python(datetime.now())


def test_list_responses_request_applies_pagination_defaults() -> None:
    """Response listing should use shared pagination defaults."""
    payload = ListSurveyResponsesRequest.model_validate({})

    assert payload.page == limits.LIST_PAGE_DEFAULT
    assert payload.page_size == limits.LIST_PAGE_SIZE_DEFAULT
    assert payload.status is None


def test_list_responses_request_rejects_unknown_status() -> None:
    """Response listing should validate the session status filter."""
    with pytest.raises(ValidationError) as exc_info:
        ListSurveyResponsesRequest.model_validate({"status": cast(Any, "not_a_status")})

    assert exc_info.value.errors()[0]["loc"] == ("status",)


class _PaginationProbe(BaseModel):
    page: int
    page_size: int


def test_pagination_fields_reject_values_outside_shared_bounds() -> None:
    """Shared pagination constants should define the accepted request range."""
    with pytest.raises(ValidationError):
        ListSurveyResponsesRequest.model_validate({"page": 0})
    with pytest.raises(ValidationError):
        ListSurveyResponsesRequest.model_validate({"page_size": limits.LIST_PAGE_SIZE_MAX + 1})
