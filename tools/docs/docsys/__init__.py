"""FlowForm's dependency-free documentation tooling package.

Front ends import focused submodules on demand so displaying help or
initializing an integration does not load the documentation tree.
"""

from __future__ import annotations

import importlib
from types import ModuleType

__all__ = [
    "contracts",
    "model",
    "gitutil",
    "index",
    "impact",
    "evidence",
    "freshness",
    "query",
    "retrieve",
    "health",
    "validate",
    "debt",
]


def __getattr__(name: str) -> ModuleType:
    if name not in __all__:
        raise AttributeError(name)
    module = importlib.import_module(f"{__name__}.{name}")
    globals()[name] = module
    return module
