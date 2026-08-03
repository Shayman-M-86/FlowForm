"""Entry point for ``python -m flowform_tools.openapi``."""

from __future__ import annotations

from flowform_tools.openapi.server import mcp


def main() -> None:
    """Run the FlowForm development MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
