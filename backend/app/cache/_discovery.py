"""Cache module discovery."""

from __future__ import annotations

import pkgutil
from importlib import import_module
from types import ModuleType
from typing import Any

from app.cache._spec import CacheSpec


def iter_cache_modules(package_name: str) -> list[tuple[str, ModuleType]]:
    package = import_module(package_name)

    modules: list[tuple[str, ModuleType]] = []
    for info in pkgutil.iter_modules(package.__path__):
        if info.name.startswith("_"):
            continue

        module = import_module(f"{package_name}.{info.name}")
        if hasattr(module, "caches"):
            modules.append((info.name, module))

    return modules


def discover_cache_specs(package_name: str) -> dict[str, tuple[CacheSpec[Any, Any], ...]]:
    discovered: dict[str, tuple[CacheSpec[Any, Any], ...]] = {}

    for namespace, module in iter_cache_modules(package_name):
        discovered[namespace] = tuple(module.caches)

    return discovered
