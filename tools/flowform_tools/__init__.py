"""FlowForm repository tooling.

Deliberately import-light: importing this package must never pull in a
subpackage's dependencies. ``flowform_tools.docsys`` and
``flowform_tools.agent_hooks`` are standard-library only so they can run from a
bare ``python3`` with no virtual environment; only ``flowform_tools.mcp``
requires third-party packages, installed via the ``mcp`` optional extra.
"""

from __future__ import annotations

from flowform_tools.paths import DOCS, ROOT, TOOLS

__all__ = ["ROOT", "TOOLS", "DOCS"]
