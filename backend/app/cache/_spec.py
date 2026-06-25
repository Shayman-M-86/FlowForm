"""Declarative cache configuration."""

from __future__ import annotations

from collections.abc import Callable, Hashable
from dataclasses import dataclass
from typing import Any, cast


def identity_key(key: Any) -> Hashable:
    return cast(Hashable, key)


@dataclass(frozen=True, slots=True, kw_only=True)
class CacheSpec[K, V]:
    """Defines one cache item and its typed lookup key rule."""

    attr: str
    ttl_seconds: int
    maxsize: int = 512
    name: str | None = None
    make_key: Callable[[K], Hashable] = identity_key

    @property
    def runtime_name(self) -> str:
        return self.name or self.attr
