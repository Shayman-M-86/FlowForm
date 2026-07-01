"""Central cache registry for the Flask application."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from flask import Flask

from app.cache._item import CacheItem
from app.cache._spec import CacheSpec

if TYPE_CHECKING:
    from app.cache.account import AccountCacheNamespace
    from app.cache.crypto import CryptoCacheNamespace
    from app.cache.sessions import SessionCacheNamespace

logger = logging.getLogger(__name__)

EXTENSION_KEY = "app_cache"


class CacheNamespace:
    """Runtime namespace containing named cache items."""

    def __init__(self, name: str, specs: Iterable[CacheSpec[Any, Any]]) -> None:
        self.name = name
        self._items: dict[str, CacheItem[Any, Any]] = {}

        for spec in specs:
            if spec.attr in self._items:
                raise ValueError(
                    f"Cache item {spec.attr!r} already registered in namespace {name!r}"
                )

            item = CacheItem(spec)
            self._items[spec.attr] = item
            setattr(self, spec.attr, item)

    def set_enabled(self, enabled: bool) -> None:
        for item in self._items.values():
            item.set_enabled(enabled)

    def clear(self) -> None:
        for item in self._items.values():
            item.clear()


class AppCache:
    """Central cache registry. One instance per app holds all cache items."""

    def __init__(self) -> None:
        self._namespaces: dict[str, CacheNamespace] = {}

    def register_namespace(
        self,
        name: str,
        specs: Iterable[CacheSpec[Any, Any]],
    ) -> None:
        if name in self._namespaces:
            raise ValueError(f"Cache namespace {name!r} already registered")
        self._namespaces[name] = CacheNamespace(name, specs)

    def init_app(self, app: Flask) -> None:
        enabled = _cache_enabled(app)
        self.set_enabled(enabled)
        app.extensions[EXTENSION_KEY] = self
        logger.debug("app cache initialized enabled=%s", enabled)

    def set_enabled(self, enabled: bool) -> None:
        for ns in self._namespaces.values():
            ns.set_enabled(enabled)

    def clear(self) -> None:
        for ns in self._namespaces.values():
            ns.clear()

    def __getattr__(self, name: str) -> CacheNamespace:
        try:
            return self._namespaces[name]
        except KeyError:
            raise AttributeError(f"No cache namespace {name!r}") from None

    if TYPE_CHECKING:

        @property
        def account(self) -> AccountCacheNamespace: ...

        @property
        def crypto(self) -> CryptoCacheNamespace: ...

        @property
        def sessions(self) -> SessionCacheNamespace: ...


def _cache_enabled(app: Flask) -> bool:
    settings = app.extensions["settings"]
    return settings.flowform.encryption.key_cache_enabled
