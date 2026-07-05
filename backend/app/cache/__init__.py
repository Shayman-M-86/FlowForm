"""Unified application cache system."""

from typing import cast

from flask import current_app

from app.cache._discovery import discover_cache_specs
from app.cache._item import CacheItem
from app.cache._locked_ttl import LockedTTLCache
from app.cache._registry import EXTENSION_KEY, AppCache, CacheNamespace
from app.cache._spec import CacheSpec


def create_app_cache() -> AppCache:
    """Build the app cache registry from discovered cache specs."""
    cache = AppCache()

    for namespace, specs in discover_cache_specs("app.cache").items():
        cache.register_namespace(namespace, specs)

    return cache


def get_app_cache() -> AppCache:
    cache = current_app.extensions.get(EXTENSION_KEY)

    if cache is None:
        raise RuntimeError("App cache is not initialized.")

    return cast(AppCache, cache)


__all__ = [
    "AppCache",
    "CacheItem",
    "CacheNamespace",
    "CacheSpec",
    "LockedTTLCache",
    "create_app_cache",
    "get_app_cache",
]
