"""Integration-test fixture placeholders for the new suite."""

from __future__ import annotations

import pytest


@pytest.fixture
def db() -> None:
    """Placeholder for the future core database session fixture."""
    pytest.skip("new_tests integration core DB fixture is not wired yet")


@pytest.fixture
def response_db() -> None:
    """Placeholder for the future response database session fixture."""
    pytest.skip("new_tests integration response DB fixture is not wired yet")


@pytest.fixture
def clean_database() -> None:
    """Placeholder for future cross-database cleanup."""
    pytest.skip("new_tests database cleanup fixture is not wired yet")

