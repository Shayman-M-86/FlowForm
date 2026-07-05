"""Contract tests for survey key loading and cache behaviour."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from app.cache import AppCache, create_app_cache
from app.crypto._internal.kms_context import SURVEY_KMS_CONTEXT_VERSION, build_survey_kms_context
from app.crypto.models import PlaintextSurveyKey
from app.crypto.survey_key import (
    clear_plaintext_survey_key,
    load_plaintext_survey_key,
    start_plaintext_survey_key_load,
    wrapped_survey_key_exists,
)
from app.schema.orm.core.survey_encryption_key import SurveyEncryptionKey

PROJECT_ID = 11
SURVEY_ID = 22
KMS_KEY_ARN = "arn:aws:kms:us-east-1:000:key/test"
WRAPPED_KEY = b"wrapped-survey-key"
PLAINTEXT_KEY = PlaintextSurveyKey(b"s" * 32)


class FakeKmsClient:
    """Small fake that records KMS decrypt calls."""

    def __init__(self, plaintext: PlaintextSurveyKey = PLAINTEXT_KEY) -> None:
        self.plaintext = plaintext
        self.decrypt_calls: list[dict[str, object]] = []

    def decrypt(self, **kwargs: object) -> dict[str, bytes]:
        self.decrypt_calls.append(kwargs)
        return {"Plaintext": self.plaintext}


@dataclass(slots=True)
class FakeClients:
    """Small fake for the crypto client bundle."""

    kms: FakeKmsClient


@dataclass(slots=True)
class FakeDb:
    """Small fake for the repository's scalar lookup."""

    record: SurveyEncryptionKey | None

    def scalar(self, _statement: object) -> SurveyEncryptionKey | None:
        return self.record


def _cache() -> AppCache:
    return create_app_cache()


def _record() -> SurveyEncryptionKey:
    return SurveyEncryptionKey(
        project_id=PROJECT_ID,
        survey_id=SURVEY_ID,
        wrapped_survey_branch_key=WRAPPED_KEY,
        kms_key_arn=KMS_KEY_ARN,
        kms_context_version=SURVEY_KMS_CONTEXT_VERSION,
    )


def _clients(kms: FakeKmsClient | None = None) -> Any:
    return FakeClients(kms=kms or FakeKmsClient())


def _db(record: SurveyEncryptionKey | None) -> Any:
    return FakeDb(record)


def test_build_survey_kms_context_binds_key_to_survey() -> None:
    """Survey KMS context should carry the stable survey binding fields."""
    assert build_survey_kms_context(project_id=PROJECT_ID, survey_id=SURVEY_ID) == {
        "purpose": "survey_branch_key",
        "project_id": str(PROJECT_ID),
        "survey_id": str(SURVEY_ID),
        "kms_context_version": str(SURVEY_KMS_CONTEXT_VERSION),
    }


def test_load_plaintext_survey_key_returns_cached_key_without_kms() -> None:
    """Cache hits should return the plaintext survey key without unwrapping."""
    cache = _cache()
    kms = FakeKmsClient()
    cache.crypto.survey_keys.put((PROJECT_ID, SURVEY_ID), PLAINTEXT_KEY)

    result = load_plaintext_survey_key(
        cast(Any, object()),
        project_id=PROJECT_ID,
        survey_id=SURVEY_ID,
        cache=cache,
        clients=_clients(kms),
    )

    assert result == PLAINTEXT_KEY
    assert kms.decrypt_calls == []


def test_load_plaintext_survey_key_unwraps_and_caches_on_miss() -> None:
    """Cache misses should unwrap the stored survey key and cache the plaintext."""
    cache = _cache()
    kms = FakeKmsClient()

    result = load_plaintext_survey_key(
        _db(_record()),
        project_id=PROJECT_ID,
        survey_id=SURVEY_ID,
        cache=cache,
        clients=_clients(kms),
    )

    assert result == PLAINTEXT_KEY
    assert cache.crypto.survey_keys.get((PROJECT_ID, SURVEY_ID)) == PLAINTEXT_KEY
    assert kms.decrypt_calls == [
        {
            "KeyId": KMS_KEY_ARN,
            "CiphertextBlob": WRAPPED_KEY,
            "EncryptionContext": build_survey_kms_context(project_id=PROJECT_ID, survey_id=SURVEY_ID),
        }
    ]


def test_start_plaintext_survey_key_load_returns_cached_resolver() -> None:
    """A cached survey key should produce an immediate resolver."""
    cache = _cache()
    cache.crypto.survey_keys.put((PROJECT_ID, SURVEY_ID), PLAINTEXT_KEY)

    resolver = start_plaintext_survey_key_load(
        cast(Any, object()),
        project_id=PROJECT_ID,
        survey_id=SURVEY_ID,
        cache=cache,
        clients=_clients(),
    )

    assert resolver() == PLAINTEXT_KEY


def test_wrapped_survey_key_exists_uses_cached_plaintext_as_conclusive_hit() -> None:
    """A cached plaintext survey key means a wrapped key exists for that survey."""
    cache = _cache()
    cache.crypto.survey_keys.put((PROJECT_ID, SURVEY_ID), PLAINTEXT_KEY)

    assert wrapped_survey_key_exists(
        cast(Any, object()),
        project_id=PROJECT_ID,
        survey_id=SURVEY_ID,
        cache=cache,
    )


def test_clear_plaintext_survey_key_evicts_cached_key() -> None:
    """Clearing a survey key should remove the plaintext survey key from cache."""
    cache = _cache()
    cache.crypto.survey_keys.put((PROJECT_ID, SURVEY_ID), PLAINTEXT_KEY)

    clear_plaintext_survey_key(project_id=PROJECT_ID, survey_id=SURVEY_ID, cache=cache)

    assert cache.crypto.survey_keys.get((PROJECT_ID, SURVEY_ID)) is None
