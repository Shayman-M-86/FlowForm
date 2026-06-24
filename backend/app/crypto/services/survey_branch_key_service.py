"""Service for KMS-wrapped survey branch keys.

Callers decide when a survey should have a branch key. This service only
loads or creates that key row and keeps plaintext branch keys in worker-local
memory for a short TTL.
"""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.crypto.cache import LockedTTLCache
from app.crypto.errors import KmsError, SurveyBranchKeyUnavailableError
from app.crypto.kms import _build_kms_client, unwrap_dek, wrap_dek
from app.repositories.core import survey_encryption_keys as survey_key_repo
from app.schema.orm.core.survey_encryption_key import SurveyEncryptionKey

logger = logging.getLogger(__name__)

SURVEY_KMS_CONTEXT_VERSION = 1

_PREFETCH_POOL = ThreadPoolExecutor(max_workers=2)

_BRANCH_KEY_LENGTH = 32


class SurveyBranchKeyService:
    """Creates, unwraps, caches, and returns survey branch keys."""

    def __init__(
        self,
        *,
        cache: LockedTTLCache[bytes],
        kms_key_arn: str,
        region: str,
        access_key_id: SecretStr,
        secret_access_key: SecretStr,
    ) -> None:
        self._cache = cache
        self._kms_key_arn = kms_key_arn
        self._region = region
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._kms_client = _build_kms_client(
            region,
            access_key_id,
            secret_access_key,
        )

    def ensure_for_survey(
        self,
        db: Session,
        *,
        project_id: int,
        survey_id: int,
    ) -> SurveyEncryptionKey:
        """Return an existing survey key row, or create one if missing."""
        existing = survey_key_repo.get_by_project_survey(
            db,
            project_id=project_id,
            survey_id=survey_id,
        )
        if existing is not None:
            return existing

        plaintext_branch_key = os.urandom(_BRANCH_KEY_LENGTH)
        context = build_survey_kms_context(project_id=project_id, survey_id=survey_id)
        try:
            wrapped_branch_key = wrap_dek(
                plaintext_branch_key,
                self._kms_key_arn,
                context,
                region=self._region,
                access_key_id=self._access_key_id,
                secret_access_key=self._secret_access_key,
                client=self._kms_client,
            )
        except KmsError as exc:
            logger.error(
                "survey_branch_key wrap_failed project_id=%s survey_id=%s kms_key_arn=%s",
                project_id,
                survey_id,
                self._kms_key_arn,
            )
            raise SurveyBranchKeyUnavailableError() from exc

        key = survey_key_repo.create(
            db,
            project_id=project_id,
            survey_id=survey_id,
            wrapped_survey_branch_key=wrapped_branch_key,
            kms_key_arn=self._kms_key_arn,
            kms_context_version=SURVEY_KMS_CONTEXT_VERSION,
        )
        self._cache.put(key.id, plaintext_branch_key)
        return key

    def get_plaintext_key(self, key: SurveyEncryptionKey) -> bytes:
        """Return the plaintext survey branch key, unwrapping via KMS on cache miss."""
        cached = self._cache.get(key.id)
        if cached is not None:
            return cached

        context = build_survey_kms_context(
            project_id=key.project_id,
            survey_id=key.survey_id,
            kms_context_version=key.kms_context_version,
        )
        try:
            logger.debug(
                "survey_branch_key source=kms_api_lookup project_id=%s survey_id=%s key_id=%s kms_key_arn=%s",
                key.project_id,
                key.survey_id,
                key.id,
                key.kms_key_arn,
            )
            plaintext_branch_key = unwrap_dek(
                key.wrapped_survey_branch_key,
                key.kms_key_arn,
                context,
                region=self._region,
                access_key_id=self._access_key_id,
                secret_access_key=self._secret_access_key,
                client=self._kms_client,
            )
        except KmsError as exc:
            logger.error(
                "survey_branch_key unwrap_failed project_id=%s survey_id=%s key_id=%s kms_key_arn=%s",
                key.project_id,
                key.survey_id,
                key.id,
                key.kms_key_arn,
            )
            raise SurveyBranchKeyUnavailableError() from exc

        self._cache.put(key.id, plaintext_branch_key)
        return plaintext_branch_key

    def prefetch_plaintext_key(
        self, key: SurveyEncryptionKey,
    ) -> Callable[[], bytes]:
        """Start branch key decryption in the background on cache miss.

        Returns a callable that blocks until the result is ready.
        On cache hit the callable returns immediately with no thread overhead.
        """
        cached = self._cache.get(key.id)
        if cached is not None:
            return lambda: cached

        future = _PREFETCH_POOL.submit(self.get_plaintext_key, key)
        return future.result

    def clear_for_key(self, key_id: uuid.UUID) -> None:
        """Remove one plaintext survey branch key from the worker-local cache."""
        self._cache.evict(key_id)


def build_survey_kms_context(
    *,
    project_id: int,
    survey_id: int,
    kms_context_version: int = SURVEY_KMS_CONTEXT_VERSION,
) -> dict[str, str]:
    return {
        "purpose": "survey_branch_key",
        "project_id": str(project_id),
        "survey_id": str(survey_id),
        "kms_context_version": str(kms_context_version),
    }
