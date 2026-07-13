#!/usr/bin/env python3
"""Tooling configuration for ``docsys``.

Defaults are chosen so every tool works with zero configuration. A repository
may override them by adding ``scripts/docs/docsys.config.json``; only the keys
present are overridden. This keeps the deterministic tools self-contained while
allowing a project to, for example, mark a documentation area as CI-critical.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from .model import ROOT

CONFIG_PATH = ROOT / "scripts" / "docs" / "docsys.config.json"


@dataclass
class Config:
    # Documents whose path matches any of these globs cause the CI review step
    # to fail when they are impacted but unmodified. Empty = never fail CI.
    critical_doc_globs: list[str] = field(default_factory=list)
    # Number of commits since verification beyond which a document is treated
    # as "review suggested" even if no related code changed.
    stale_commit_distance: int = 200
    # Weight applied to change-trigger matches relative to related_code.
    trigger_weight: float = 0.6

    @classmethod
    def load(cls) -> "Config":
        cfg = cls()
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text())
            except (json.JSONDecodeError, OSError):
                return cfg
            for key, value in data.items():
                if hasattr(cfg, key):
                    setattr(cfg, key, value)
        return cfg
