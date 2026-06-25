"""Survey key lifecycle: create, load, prefetch, and clear.

Tier 1 of the key hierarchy. A survey key wraps every session key for one
survey. It is wrapped under KMS for storage and cached after first unwrap.
The plaintext key is cached under (project_id, survey_id) so reads never
hit the database on a cache hit. See _internal/KEY_HIERARCHY.md.
"""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session

from app.cache import get_app_cache
from app.cache.crypto import SurveyKeyCacheKey
from app.core.config import current_settings
from app.crypto._internal.errors import KmsError, SurveyBranchKeyUnavailableError
from app.crypto._internal.kms_context import (
    SURVEY_KMS_CONTEXT_VERSION,
    build_survey_kms_context,
)
from app.crypto._internal.wrapping import unwrap_survey_key, wrap_survey_key
from app.crypto.models import PlaintextSurveyKey, SurveyKeyResolver, WrappedSurveyKey
from app.repositories.core import survey_encryption_keys as survey_key_repo
from app.schema.orm.core.survey_encryption_key import SurveyEncryptionKey

logger = logging.getLogger(__name__)

_SURVEY_KEY_LENGTH = 32
_PREFETCH_POOL = ThreadPoolExecutor(max_workers=2)


def create_wrapped_survey_key(
    db: Session,
    *,
    project_id: int,
    survey_id: int,
) -> SurveyEncryptionKey:
    """Mint, wrap, and persist a new survey key.

    Called when a survey is published. Caller ensures one does not already
    exist. Side effects: KMS wrap + DB write + cache write.
    """
    kms_key_arn = current_settings().flowform.encryption.kms_key_arn
    plaintext_survey_key = PlaintextSurveyKey(os.urandom(_SURVEY_KEY_LENGTH))
    context = build_survey_kms_context(project_id=project_id, survey_id=survey_id)

    try:
        wrapped_survey_key = wrap_survey_key(plaintext_survey_key, kms_key_arn, context)
    except KmsError as exc:
        logger.error("survey_key wrap_failed survey_id=%s", survey_id)
        raise SurveyBranchKeyUnavailableError() from exc

    record = survey_key_repo.create(
        db,
        project_id=project_id,
        survey_id=survey_id,
        wrapped_survey_branch_key=wrapped_survey_key,
        kms_key_arn=kms_key_arn,
        kms_context_version=SURVEY_KMS_CONTEXT_VERSION,
    )
    get_app_cache().crypto.survey_keys.put((project_id, survey_id), plaintext_survey_key)
    return record


def wrapped_survey_key_exists(
    db: Session,
    *,
    project_id: int,
    survey_id: int,
) -> bool:
    """Return whether a survey key exists for the given survey.

    Checks the cache first; a plaintext key can only be cached if one was
    created, so a hit is conclusive. On a miss, falls back to the DB.
    Side effects: cache read; on miss, DB read.
    """
    if get_app_cache().crypto.survey_keys.get((project_id, survey_id)) is not None:
        return True

    record = survey_key_repo.get_by_project_survey(
        db,
        project_id=project_id,
        survey_id=survey_id,
    )
    return record is not None


def load_plaintext_survey_key(
    db: Session,
    *,
    project_id: int,
    survey_id: int,
) -> PlaintextSurveyKey:
    """Return the plaintext survey key, unwrapping on cache miss.

    Checks the cache by (project_id, survey_id) first, so a cache hit
    returns immediately with no database access. On a miss, fetches the
    wrapped record and unwraps it via KMS. Side effects: cache read; on
    miss, DB read + KMS unwrap + cache write.
    """
    cached = get_app_cache().crypto.survey_keys.get((project_id, survey_id))
    if cached is not None:
        return cached

    record = _get_wrapped_record(db, project_id=project_id, survey_id=survey_id)
    return _unwrap_and_cache(record)


def start_plaintext_survey_key_load(
    db: Session,
    *,
    project_id: int,
    survey_id: int,
) -> SurveyKeyResolver:
    """Begin loading the plaintext survey key, returning a resolver for the result.

    On a cache miss the wrapped record is fetched on the calling thread
    (which owns the DB session) and only the KMS unwrap runs in the
    background, so it can overlap with other work. Call the returned
    resolver to block until the key is ready. Side effects: cache read;
    on miss, DB read now + a background KMS unwrap.
    """
    cached = get_app_cache().crypto.survey_keys.get((project_id, survey_id))
    if cached is not None:
        return lambda: cached

    record = _get_wrapped_record(db, project_id=project_id, survey_id=survey_id)
    future = _PREFETCH_POOL.submit(_unwrap_and_cache, record)
    return future.result


def clear_plaintext_survey_key(*, project_id: int, survey_id: int) -> None:
    """Evict a plaintext survey key from the cache."""
    get_app_cache().crypto.survey_keys.evict((project_id, survey_id))


def _get_wrapped_record(
    db: Session,
    *,
    project_id: int,
    survey_id: int,
) -> SurveyEncryptionKey:
    """Fetch the wrapped survey key row, raising if it does not exist."""
    record = survey_key_repo.get_by_project_survey(
        db,
        project_id=project_id,
        survey_id=survey_id,
    )
    if record is None:
        raise SurveyBranchKeyUnavailableError()
    return record


def _unwrap_and_cache(record: SurveyEncryptionKey) -> PlaintextSurveyKey:
    """Unwrap a record's key via KMS and cache it. No DB access."""
    cache_key: SurveyKeyCacheKey = (record.project_id, record.survey_id)
    context = build_survey_kms_context(
        project_id=record.project_id,
        survey_id=record.survey_id,
        kms_context_version=record.kms_context_version,
    )

    try:
        plaintext_survey_key = unwrap_survey_key(
            WrappedSurveyKey(record.wrapped_survey_branch_key),
            record.kms_key_arn,
            context,
        )
    except KmsError as exc:
        logger.error("survey_key unwrap_failed survey_id=%s", record.survey_id)
        raise SurveyBranchKeyUnavailableError() from exc

    get_app_cache().crypto.survey_keys.put(cache_key, plaintext_survey_key)
    return plaintext_survey_key
