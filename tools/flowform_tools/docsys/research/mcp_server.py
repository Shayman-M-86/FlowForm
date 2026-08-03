"""One-tool MCP surface for pre-warmed FlowForm documentation research."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from .models import ResearchRequest, ResearchRuntimeError
from .session_pool import ResearchSessionPool

_pool: ResearchSessionPool | None = None


@asynccontextmanager
async def _lifespan(_server: FastMCP) -> AsyncIterator[None]:
    global _pool
    pool = ResearchSessionPool()
    await pool.start()
    _pool = pool
    try:
        yield
    finally:
        _pool = None
        await pool.close()


mcp = FastMCP(
    "flowform-doc-research",
    instructions=(
        "Use the single research tool only when a separate source-backed FlowForm "
        "documentation briefing is useful."
    ),
    lifespan=_lifespan,
)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def research(
    question: str,
    depth: Literal["quick", "thorough"] = "quick",
    scope: str | None = None,
) -> dict[str, Any]:
    """Answer one exact FlowForm question with cited repository evidence."""
    if _pool is None:
        raise ToolError("research session pool is not initialized")
    try:
        return await _pool.research(
            ResearchRequest(
                question=question,
                depth=depth,
                scope=scope,
                provider="auto",
            )
        )
    except (ValueError, ResearchRuntimeError) as exc:
        raise ToolError(str(exc)) from exc


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
