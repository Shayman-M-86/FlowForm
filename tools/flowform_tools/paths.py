"""Shared repository path anchors for FlowForm tooling.

Every tool resolves the repository root from here instead of recomputing
``Path(__file__).parents[N]`` with a different ``N`` per module.
"""

from __future__ import annotations

from pathlib import Path

# flowform_tools/paths.py -> flowform_tools -> tools -> repository root.
ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
DOCS = ROOT / "docs"
