from __future__ import annotations

import os

import pytest


def require_live_env(name: str) -> str:
    """Return one required live-test input without exposing its value."""
    value = os.environ.get(name, "").strip()
    if not value:
        pytest.fail(f"Live external test requires {name}", pytrace=False)
    return value
