from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.public_submissions.core.actions.session_starter import SessionStarter


@pytest.fixture(autouse=True)
def _mock_survey_branch_key_layer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch the survey branch-key layer so response tests run without a real
    survey_encryption_keys row or KMS calls."""
    fake_survey_key = MagicMock()

    monkeypatch.setattr(
        "app.services.public_submissions.core.actions.session_starter.load_survey_encryption_key",
        lambda *_args, **_kwargs: fake_survey_key,
    )
    monkeypatch.setattr(
        "app.services.public_submissions.core.shared.session_crypto.load_survey_encryption_key",
        lambda *_args, **_kwargs: fake_survey_key,
    )

    branch_key_svc = MagicMock()
    branch_key_svc.get_plaintext_key.return_value = b"\x03" * 32
    branch_key_svc.ensure_for_survey.return_value = MagicMock()

    original_init = SessionStarter.__init__

    def patched_init(self, **kwargs):
        kwargs.setdefault("survey_branch_key_service", branch_key_svc)
        original_init(self, **kwargs)

    monkeypatch.setattr(SessionStarter, "__init__", patched_init)
