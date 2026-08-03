"""Pre-warmed, single-use Claude Agent SDK sessions for Docsys research."""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, ResultMessage

from ..core.model import ROOT
from .models import (
    RESULT_SCHEMA,
    ResearchRequest,
    ResearchRuntimeError,
    validate_result,
)
from .prompt import build_prompt

_SANDBOX_LAUNCHER = ROOT / "tools/bin/docsys-claude-sandbox"
_LOCAL_AUTH_CONFLICTS = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_FOUNDRY",
    "CLAUDE_CODE_USE_VERTEX",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "GOOGLE_APPLICATION_CREDENTIALS",
)


def sanitize_local_auth_environment() -> None:
    """Force SDK subprocesses to use the installed Claude Code login."""
    for name in _LOCAL_AUTH_CONFLICTS:
        os.environ.pop(name, None)


def _allowed_bash_tools() -> list[str]:
    docsys = ROOT / "tools/bin/docsys"
    return [
        f"Bash({docsys} find:*)",
        f"Bash({docsys} read:*)",
        "Bash(rg:*)",
        "Bash(fd:*)",
        "Bash(ast-grep:*)",
        "Bash(jq:*)",
        "Bash(yq:*)",
        "Bash(sed:*)",
        "Bash(nl:*)",
    ]


def _options(request: ResearchRequest, *, workspace: Path) -> ClaudeAgentOptions:
    if shutil.which("claude") is None:
        raise ResearchRuntimeError("Claude Code CLI is not installed")
    if shutil.which("bwrap") is None:
        raise ResearchRuntimeError(
            "bubblewrap is required for read-only Claude research"
        )
    if not _SANDBOX_LAUNCHER.is_file():
        raise ResearchRuntimeError("Claude research sandbox launcher is missing")
    return ClaudeAgentOptions(
        cli_path=_SANDBOX_LAUNCHER,
        cwd=workspace,
        add_dirs=[ROOT],
        tools=["Bash"],
        allowed_tools=_allowed_bash_tools(),
        strict_mcp_config=True,
        mcp_servers={},
        permission_mode="dontAsk",
        setting_sources=[],
        model=request.resolved_claude_model,
        effort=request.reasoning_effort,
        max_turns=request.max_turns,
        output_format={"type": "json_schema", "schema": RESULT_SCHEMA},
        env={
            "CLAUDE_CODE_SKIP_PROMPT_HISTORY": "1",
            "DISABLE_AUTOUPDATER": "1",
            "NO_COLOR": "1",
        },
        extra_args={
            "safe-mode": None,
            "disable-slash-commands": None,
            "no-chrome": None,
            "no-session-persistence": None,
        },
    )


class WarmClaudeSession:
    """One initialized Claude subprocess that serves exactly one research call."""

    def __init__(
        self,
        *,
        request: ResearchRequest,
        temporary: tempfile.TemporaryDirectory[str],
        client: ClaudeSDKClient,
    ) -> None:
        self.request = request
        self._temporary = temporary
        self._client = client
        self._used = False

    @classmethod
    async def create(cls, depth: str) -> WarmClaudeSession:
        request = ResearchRequest(
            question="warm session", depth=depth, provider="claude"
        )
        temporary = tempfile.TemporaryDirectory(prefix="flowform-doc-research-")
        workspace = Path(temporary.name)
        client = ClaudeSDKClient(_options(request, workspace=workspace))
        try:
            await client.connect()
        except Exception as exc:
            temporary.cleanup()
            raise ResearchRuntimeError(
                f"Claude SDK initialization failed: {exc}"
            ) from exc
        return cls(request=request, temporary=temporary, client=client)

    async def research(self, request: ResearchRequest) -> dict[str, Any]:
        if self._used:
            raise ResearchRuntimeError("a warm Claude session cannot be reused")
        if request.depth != self.request.depth:
            raise ResearchRuntimeError(
                "warm Claude session depth does not match request"
            )
        self._used = True
        started = time.monotonic()
        result_message: ResultMessage | None = None
        try:
            await self._client.query(build_prompt(request))
            async for message in self._client.receive_response():
                if isinstance(message, ResultMessage):
                    result_message = message
        except Exception as exc:
            raise ResearchRuntimeError(f"Claude SDK research failed: {exc}") from exc
        if result_message is None:
            raise ResearchRuntimeError("Claude SDK returned no result message")
        if result_message.subtype != "success" or result_message.is_error:
            detail = result_message.result or "; ".join(result_message.errors or [])
            raise ResearchRuntimeError(
                f"Claude SDK research failed: {(detail or result_message.subtype)[:500]}"
            )
        if not isinstance(result_message.structured_output, dict):
            raise ResearchRuntimeError("Claude SDK did not return structured output")
        result = validate_result(result_message.structured_output, scope=request.scope)
        result["runtime"] = {
            "provider": "claude-agent-sdk",
            "authentication": "local-claude-code-login",
            "model": request.resolved_claude_model,
            "depth": request.depth,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
            "run_id": result_message.session_id,
            "fresh_session": True,
            "persisted": False,
            "filesystem": "bubblewrap-read-only",
            "prewarmed": True,
        }
        return result

    async def close(self) -> None:
        try:
            await self._client.disconnect()
        finally:
            self._temporary.cleanup()


async def run_claude_once(request: ResearchRequest) -> dict[str, Any]:
    """Run one SDK-backed request outside the long-lived MCP pool."""
    sanitize_local_auth_environment()
    session = await WarmClaudeSession.create(request.depth)
    try:
        return await asyncio.wait_for(
            session.research(request), timeout=request.timeout_seconds
        )
    except TimeoutError as exc:
        raise ResearchRuntimeError(
            f"Claude SDK research exceeded {request.timeout_seconds} seconds"
        ) from exc
    finally:
        await session.close()


class ResearchSessionPool:
    """Maintain one pre-initialized, single-use Claude session per depth."""

    def __init__(self) -> None:
        self._sessions: dict[str, WarmClaudeSession | None] = {
            "quick": None,
            "thorough": None,
        }
        self._locks = {depth: asyncio.Lock() for depth in self._sessions}

    async def start(self) -> None:
        sanitize_local_auth_environment()
        warmed = await asyncio.gather(
            *(WarmClaudeSession.create(depth) for depth in self._sessions),
            return_exceptions=True,
        )
        for depth, value in zip(self._sessions, warmed, strict=True):
            self._sessions[depth] = (
                value if isinstance(value, WarmClaudeSession) else None
            )

    async def research(self, request: ResearchRequest) -> dict[str, Any]:
        """Consume a warm session, replenish it, and fall back to Codex on failure."""
        from .codex import run_codex

        claude_error: ResearchRuntimeError | None = None
        async with self._locks[request.depth]:
            session = self._sessions[request.depth]
            if session is None:
                try:
                    session = await WarmClaudeSession.create(request.depth)
                except ResearchRuntimeError as exc:
                    claude_error = exc
            replacement: asyncio.Task[WarmClaudeSession] | None = None
            if session is not None:
                replacement = asyncio.create_task(
                    WarmClaudeSession.create(request.depth)
                )
                try:
                    result = await asyncio.wait_for(
                        session.research(request), timeout=request.timeout_seconds
                    )
                except TimeoutError:
                    claude_error = ResearchRuntimeError(
                        f"Claude SDK research exceeded {request.timeout_seconds} seconds"
                    )
                except ResearchRuntimeError as exc:
                    claude_error = exc
                else:
                    return result
                finally:
                    await session.close()
                    try:
                        self._sessions[request.depth] = await replacement
                    except ResearchRuntimeError:
                        self._sessions[request.depth] = None

        try:
            result = await asyncio.to_thread(run_codex, request)
        except ResearchRuntimeError as codex_error:
            raise ResearchRuntimeError(
                f"Claude primary failed ({claude_error}); "
                f"Codex fallback failed ({codex_error})"
            ) from codex_error
        result["runtime"]["fallback_from"] = "claude-agent-sdk"
        result["runtime"]["fallback_reason"] = str(claude_error)[:500]
        return result

    async def close(self) -> None:
        sessions = [session for session in self._sessions.values() if session]
        await asyncio.gather(*(session.close() for session in sessions))
        for depth in self._sessions:
            self._sessions[depth] = None
