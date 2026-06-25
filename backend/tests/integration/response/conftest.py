from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from app.crypto.models import (
    LinkageKey,
    NewSessionKey,
    NewSessionLocator,
    PlaintextSessionKey,
    SessionLocator,
    WrappedSessionKey,
)

_FAKE_LINKAGE_KEY = LinkageKey(version=1, secret=b"\xcc" * 32, aws_version_id="test-version")
_FAKE_SESSION_LOCATOR = SessionLocator(os.urandom(32))
_FAKE_PLAINTEXT_DEK = PlaintextSessionKey(os.urandom(32))
_FAKE_WRAPPED_DEK = WrappedSessionKey(b"\x02" * 64)

_STARTER_MODULE = "app.services.public_submissions.core.actions.session_starter"
_LOADER_MODULE = "app.services.public_submissions.core.session_loader"
_ANSWER_SAVE_MODULE = "app.services.public_submissions.core.actions.answer_save"


@pytest.fixture(autouse=True)
def _mock_crypto_layer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch module-level crypto calls so response integration tests run without AWS."""
    monkeypatch.setattr(
        f"{_STARTER_MODULE}.load_current_linkage_key",
        lambda _db: _FAKE_LINKAGE_KEY,
    )
    monkeypatch.setattr(
        f"{_STARTER_MODULE}.derive_session_locator",
        lambda _sid, _key: NewSessionLocator(
            linkage_key_version=1,
            session_locator=_FAKE_SESSION_LOCATOR,
        ),
    )
    monkeypatch.setattr(
        f"{_STARTER_MODULE}.start_plaintext_survey_key_load",
        lambda _db, **_kw: MagicMock(return_value=os.urandom(32)),
    )
    monkeypatch.setattr(
        f"{_STARTER_MODULE}.create_session_key",
        lambda _ctx, _survey_key: NewSessionKey(
            plaintext_key=_FAKE_PLAINTEXT_DEK,
            wrapped_key=_FAKE_WRAPPED_DEK,
        ),
    )
    monkeypatch.setattr(
        f"{_LOADER_MODULE}.resolve_existing_session_locator",
        lambda _db, _sid, _ver: (_FAKE_SESSION_LOCATOR, _FAKE_LINKAGE_KEY),
    )
