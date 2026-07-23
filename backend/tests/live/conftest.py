from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def forbid_live_external_tests_in_ci() -> None:
    """Fail before any outbound request if live tests are selected in CI."""
    if os.environ.get("CI", "").lower() not in {"", "0", "false", "no"}:
        pytest.fail("Live external tests are disabled when CI is set", pytrace=False)
