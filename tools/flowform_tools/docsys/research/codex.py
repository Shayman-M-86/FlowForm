"""Isolated local Codex fallback for Docsys research."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from .models import (
    RESULT_SCHEMA,
    ResearchRequest,
    ResearchRuntimeError,
    validate_result,
)
from .prompt import build_prompt


def codex_command(
    request: ResearchRequest,
    *,
    workspace: Path,
    schema_path: Path,
    output_path: Path,
) -> list[str]:
    return [
        shutil.which("codex") or "codex",
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--strict-config",
        "--disable",
        "memories",
        "--disable",
        "apps",
        "--disable",
        "browser_use",
        "--disable",
        "multi_agent",
        "--disable",
        "image_generation",
        "--disable",
        "hooks",
        "--sandbox",
        "read-only",
        "--skip-git-repo-check",
        "--cd",
        str(workspace),
        "--model",
        request.resolved_codex_model,
        "--config",
        f'model_reasoning_effort="{request.codex_reasoning_effort}"',
        "--config",
        "project_doc_max_bytes=0",
        "--config",
        "memories.use_memories=false",
        "--config",
        "memories.generate_memories=false",
        "--config",
        'shell_environment_policy.inherit="all"',
        "--output-schema",
        str(schema_path),
        "--output-last-message",
        str(output_path),
        "--json",
        "-",
    ]


def _clean_environment() -> dict[str, str]:
    allowed = {
        "CODEX_HOME",
        "DBUS_SESSION_BUS_ADDRESS",
        "HOME",
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "LANG",
        "LOGNAME",
        "NO_PROXY",
        "NODE_EXTRA_CA_CERTS",
        "PATH",
        "REQUESTS_CA_BUNDLE",
        "SHELL",
        "SSL_CERT_DIR",
        "SSL_CERT_FILE",
        "TERM",
        "TMPDIR",
        "USER",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_RUNTIME_DIR",
    }
    environment = {
        name: value
        for name, value in os.environ.items()
        if name in allowed or name.startswith("LC_")
    }
    environment["NO_COLOR"] = "1"
    return environment


def _decode_result(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```json") and text.endswith("```"):
        text = text[7:-3].strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ResearchRuntimeError("Codex returned invalid structured output") from exc
    if not isinstance(value, dict):
        raise ResearchRuntimeError("Codex result must be a JSON object")
    return value


def run_codex(request: ResearchRequest) -> dict[str, Any]:
    if shutil.which("codex") is None:
        raise ResearchRuntimeError("Codex CLI is not installed")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="flowform-doc-research-") as temporary:
        workspace = Path(temporary)
        schema_path = workspace / "result-schema.json"
        output_path = workspace / "result.json"
        schema_path.write_text(json.dumps(RESULT_SCHEMA, separators=(",", ":")))
        try:
            completed = subprocess.run(
                codex_command(
                    request,
                    workspace=workspace,
                    schema_path=schema_path,
                    output_path=output_path,
                ),
                input=build_prompt(request),
                text=True,
                capture_output=True,
                timeout=request.timeout_seconds,
                env=_clean_environment(),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ResearchRuntimeError(
                f"Codex research exceeded {request.timeout_seconds} seconds"
            ) from exc
        if completed.returncode != 0:
            detail = completed.stderr.strip().splitlines()
            message = detail[-1][:500] if detail else "no diagnostic available"
            raise ResearchRuntimeError(f"Codex research failed: {message}")
        if not output_path.is_file():
            raise ResearchRuntimeError("Codex did not produce a final result")
        result = validate_result(
            _decode_result(output_path.read_text()), scope=request.scope
        )

    result["runtime"] = {
        "provider": "codex",
        "authentication": "local-cli-login",
        "model": request.resolved_codex_model,
        "depth": request.depth,
        "elapsed_ms": round((time.monotonic() - started) * 1000),
        "run_id": str(uuid.uuid4()),
        "fresh_session": True,
        "persisted": False,
        "filesystem": "codex-read-only-sandbox",
        "prewarmed": False,
    }
    return result
