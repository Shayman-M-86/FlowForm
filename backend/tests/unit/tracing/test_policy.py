"""Attribute-policy behaviour tests.

There is no runtime strict mode: policy violations are always dropped and
logged, never raised. These tests are the safety net that a mislabelled field
or unsupported value is caught — they assert directly on ``filter_fields``
(and the normalizers) rather than on a runtime switch.
"""

from __future__ import annotations

import logging

import pytest

from app.tracing import policy
from app.tracing.vocabulary import (
    FIELD_PREFIX,
    MAX_ABS_INT,
    MAX_SEQUENCE_LENGTH,
    MAX_STRING_LENGTH,
)


def test_allowed_fields_are_prefixed_and_kept() -> None:
    result = policy.filter_fields({"outcome": "accepted", "answer_count": 3})

    assert result == {
        f"{FIELD_PREFIX}outcome": "accepted",
        f"{FIELD_PREFIX}answer_count": 3,
    }


def test_unknown_field_is_dropped() -> None:
    assert policy.filter_fields({"not_allowed": "x"}) == {}


def test_sensitive_name_is_dropped_even_if_allowlisted_shape() -> None:
    # 'email' is not in the allowlist, but the sensitive-key check is the second
    # guard; a name that were ever both allowlisted and sensitive still drops.
    assert policy.filter_fields({"email": "a@b.com"}) == {}


def test_none_value_is_dropped_silently() -> None:
    assert policy.filter_fields({"outcome": None}) == {}


def test_string_is_truncated() -> None:
    result = policy.filter_fields({"outcome": "x" * (MAX_STRING_LENGTH + 50)})

    assert result[f"{FIELD_PREFIX}outcome"] == "x" * MAX_STRING_LENGTH


def test_bool_stays_bool_not_int() -> None:
    result = policy.filter_fields({"outcome": True})

    value = result[f"{FIELD_PREFIX}outcome"]
    assert value is True
    assert isinstance(value, bool)


def test_out_of_range_int_is_dropped() -> None:
    assert policy.filter_fields({"answer_count": MAX_ABS_INT + 1}) == {}


def test_non_finite_float_is_dropped() -> None:
    # 'answer_count' is allowlisted; a non-finite float under it drops on the
    # value check, not the allowlist check.
    assert policy.filter_fields({"answer_count": float("inf")}) == {}
    assert policy.normalize_value(float("nan")) is None


def test_field_count_is_capped(monkeypatch: pytest.MonkeyPatch) -> None:
    # The allowlist is smaller than MAX_FIELDS, so exercise the cap with a
    # lowered bound and a wider allowlist rather than 24+ real fields.
    monkeypatch.setattr(policy, "MAX_FIELDS", 2)
    monkeypatch.setattr(policy, "ALLOWED_FIELDS", frozenset({"a", "b", "c"}))

    result = policy.filter_fields({"a": 1, "b": 2, "c": 3})

    assert len(result) == 2


def test_homogeneous_sequence_is_kept() -> None:
    result = policy.filter_fields({"outcome": ["a", "b", "c"]})

    assert result[f"{FIELD_PREFIX}outcome"] == ["a", "b", "c"]


def test_sequence_is_length_capped() -> None:
    result = policy.filter_fields({"answer_count": list(range(MAX_SEQUENCE_LENGTH + 5))})

    assert result[f"{FIELD_PREFIX}answer_count"] == list(range(MAX_SEQUENCE_LENGTH))


def test_mixed_type_sequence_is_dropped() -> None:
    assert policy.filter_fields({"outcome": [True, 1]}) == {}


def test_sequence_with_unsupported_element_is_dropped() -> None:
    assert policy.filter_fields({"outcome": ["a", object()]}) == {}


def test_reject_logs_at_warning_and_never_raises(caplog: pytest.LogCaptureFixture) -> None:
    policy._drop_count = 0  # reset throttle so the first drop logs
    with caplog.at_level(logging.WARNING, logger="app.tracing"):
        result = policy.filter_fields({"not_allowed": "x"})

    assert result == {}
    assert any("tracing policy drop" in r.message for r in caplog.records)


def test_reject_is_throttled(caplog: pytest.LogCaptureFixture) -> None:
    policy._drop_count = 0
    with caplog.at_level(logging.WARNING, logger="app.tracing"):
        for _ in range(policy._LOG_INTERVAL + 5):
            policy.reject("boom")

    # One log at count 0, one at the interval boundary; not one per call.
    warnings = [r for r in caplog.records if "boom" in r.message]
    assert 1 <= len(warnings) <= 2
