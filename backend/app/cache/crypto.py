"""Crypto cache definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from app.cache._item import CacheItem
from app.cache._spec import CacheSpec

if TYPE_CHECKING:
    from app.crypto.models import LinkageKey, PlaintextSessionKey, PlaintextSurveyKey

# (project_id, survey_id) — the stable identity a survey key is cached under.
SurveyKeyCacheKey = tuple[int, int]


current_linkage_key: CacheSpec[str, LinkageKey] = CacheSpec(
    attr="current_linkage_key",
    maxsize=1,
    ttl_seconds=1800,
)

linkage_keys_by_version: CacheSpec[int, LinkageKey] = CacheSpec(
    attr="linkage_keys_by_version",
    maxsize=16,
    ttl_seconds=1800,
)

survey_keys: CacheSpec[SurveyKeyCacheKey, PlaintextSurveyKey] = CacheSpec(
    attr="survey_keys",
    maxsize=512,
    ttl_seconds=600,
)

session_deks: CacheSpec[UUID, PlaintextSessionKey] = CacheSpec(
    attr="session_deks",
    maxsize=10_000,
    ttl_seconds=1800,
)

caches = (
    current_linkage_key,
    linkage_keys_by_version,
    survey_keys,
    session_deks,
)


class CryptoCacheNamespace(Protocol):
    """Typed crypto cache namespace exposed by the app cache registry."""

    current_linkage_key: CacheItem[str, LinkageKey]
    linkage_keys_by_version: CacheItem[int, LinkageKey]
    survey_keys: CacheItem[SurveyKeyCacheKey, PlaintextSurveyKey]
    session_deks: CacheItem[UUID, PlaintextSessionKey]
