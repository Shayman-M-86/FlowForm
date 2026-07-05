"""Unit-test fixtures for isolated new test modules."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import pytest


@dataclass
class FakeRepository:
    """Small in-memory call recorder for unit tests."""

    calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = field(default_factory=list)

    def record(self, name: str, *args: Any, **kwargs: Any) -> None:
        """Record a repository-style call."""
        self.calls.append((name, args, kwargs))


@dataclass
class FakeCache:
    """Tiny cache double with get/set/evict semantics."""

    values: dict[Any, Any] = field(default_factory=dict)

    def get(self, key: Any) -> Any | None:
        """Return a cached value when present."""
        return self.values.get(key)

    def set(self, key: Any, value: Any) -> None:
        """Store a cached value."""
        self.values[key] = value

    def evict(self, key: Any) -> None:
        """Remove a cached value when present."""
        self.values.pop(key, None)


@pytest.fixture
def fake_repo() -> FakeRepository:
    """Return a generic repository test double."""
    return FakeRepository()


@pytest.fixture
def fake_cache() -> FakeCache:
    """Return a generic cache test double."""
    return FakeCache()


@pytest.fixture
def no_db() -> Callable[..., None]:
    """Return a callable that fails when a unit test accidentally reaches for a DB."""

    def _fail(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("Unit tests should not use a real database session")

    return _fail

