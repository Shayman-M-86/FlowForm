"""Fresh local Codex process orchestration for source-backed research."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

from ..command_catalog import render_research_cli_policy
from ..core.model import ROOT

DEFAULT_QUICK_MODEL = "gpt-5.6-terra"
DEFAULT_THOROUGH_MODEL = "gpt-5.6-sol"
DEPTHS = frozenset({"quick", "thorough"})
_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")
_PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "research.md"

class ResearchRuntimeError(RuntimeError):
    """A fresh local Codex research process failed."""


class ResearchSource(BaseModel):
    """One source citation returned by the isolated research session."""

    model_config = ConfigDict(extra="forbid")

    path: str
    start_line: StrictInt = Field(ge=1)
    end_line: StrictInt = Field(ge=1)
    kind: Literal["documentation", "implementation", "test", "configuration"]

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: str, info: ValidationInfo) -> str:
        path = PurePosixPath(value)
        if value.startswith("/") or any(part in {"", ".", ".."} for part in path.parts):
            raise ValueError("source path must be repository-relative")
        normalized = path.as_posix()
        scope = info.context.get("scope") if isinstance(info.context, dict) else None
        if scope is not None and not (
            normalized == scope or normalized.startswith(scope + "/")
        ):
            raise ValueError(f"cited source is outside requested scope: {value}")
        resolved = ROOT.joinpath(*path.parts)
        if resolved.is_symlink() or not resolved.is_file():
            raise ValueError(f"cited source does not exist: {value}")
        return normalized

    @model_validator(mode="after")
    def _validate_lines(self) -> "ResearchSource":
        if self.end_line < self.start_line:
            raise ValueError("source line range is invalid")
        resolved = ROOT.joinpath(*PurePosixPath(self.path).parts)
        line_count = len(resolved.read_text(errors="replace").splitlines())
        if self.end_line > max(1, line_count):
            raise ValueError(f"cited line is beyond end of file: {self.path}")
        return self


class ResearchFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: str
    sources: list[ResearchSource] = Field(min_length=1, max_length=6)
    snippet: str | None

    @field_validator("claim")
    @classmethod
    def _strip_claim(cls, value: str) -> str:
        return value.strip()


class ResearchResult(BaseModel):
    """Validated result shape and generated schema for Codex research."""

    model_config = ConfigDict(extra="forbid")

    answer: str
    confidence: Literal["high", "medium", "low"]
    basis: Literal["documentation", "implementation", "mixed"]
    findings: list[ResearchFinding] = Field(min_length=1, max_length=12)
    contradictions: list[str] = Field(max_length=20)
    unresolved: list[str] = Field(max_length=20)

    @field_validator("answer")
    @classmethod
    def _validate_answer(cls, value: str) -> str:
        answer = value.strip()
        if not answer:
            raise ValueError("answer must be a non-empty string")
        return answer

    @field_validator("contradictions", "unresolved")
    @classmethod
    def _strip_text_lists(cls, values: list[str]) -> list[str]:
        return [item.strip() for item in values if item.strip()]


RESULT_SCHEMA: dict[str, Any] = ResearchResult.model_json_schema()


@dataclass(frozen=True)
class ResearchRequest:
    question: str
    depth: str = "quick"
    model: str | None = None
    scope: str | None = None

    def __post_init__(self) -> None:
        question = self.question.strip()
        depth = self.depth.casefold().strip()
        if not question:
            raise ValueError("question must not be empty")
        if len(question) > 4_000:
            raise ValueError("question must contain at most 4000 characters")
        if depth not in DEPTHS:
            raise ValueError("depth must be one of: quick, thorough")
        if self.model is not None and not _MODEL_RE.fullmatch(self.model.strip()):
            raise ValueError("model contains unsupported characters")
        if self.scope is not None:
            raw_scope = self.scope.strip().replace("\\", "/").rstrip("/")
            path = PurePosixPath(raw_scope)
            if (
                not raw_scope
                or raw_scope.startswith("/")
                or any(part in {"", ".", ".."} for part in path.parts)
            ):
                raise ValueError("scope must be a normalized repository-relative path")
            object.__setattr__(self, "scope", path.as_posix())
        object.__setattr__(self, "question", question)
        object.__setattr__(self, "depth", depth)
        if self.model is not None:
            object.__setattr__(self, "model", self.model.strip())

    @property
    def resolved_model(self) -> str:
        return self.model or (
            DEFAULT_QUICK_MODEL if self.depth == "quick" else DEFAULT_THOROUGH_MODEL
        )

    @property
    def reasoning_effort(self) -> str:
        return "medium" if self.depth == "quick" else "high"

    @property
    def timeout_seconds(self) -> int:
        return 120 if self.depth == "quick" else 240


def _prompt(request: ResearchRequest) -> str:
    instructions = (
        _PROMPT_PATH.read_text()
        .strip()
        .replace("{{RESEARCH_CLI_TOOLS}}", render_research_cli_policy())
    )
    payload = (
        json.dumps(
            {
                "scope": request.scope or "repository-wide",
                "depth": request.depth,
                "question": request.question,
                "repository_root": str(ROOT),
                "docsys_command": str(ROOT / "tools/bin/docsys"),
            },
            ensure_ascii=False,
            indent=2,
        )
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )
    return (
        f"{instructions}\n\n"
        "<research_request_json>\n"
        f"{payload}\n"
        "</research_request_json>\n"
    )


def _codex_command(
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
        request.resolved_model,
        "--config",
        f'model_reasoning_effort="{request.reasoning_effort}"',
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


def _validate_result(
    value: dict[str, Any], *, scope: str | None = None
) -> dict[str, Any]:
    try:
        result = ResearchResult.model_validate(value, context={"scope": scope})
    except ValidationError as exc:
        messages = [str(error["msg"]) for error in exc.errors()]
        raise ResearchRuntimeError("; ".join(messages)) from exc
    return result.model_dump(mode="json")


def run_research(request: ResearchRequest) -> dict[str, Any]:
    """Run one fresh, non-persistent Codex process and validate its citations."""
    if shutil.which("codex") is None:
        raise ResearchRuntimeError("Codex CLI is not installed")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="flowform-doc-research-") as temporary:
        workspace = Path(temporary)
        schema_path = workspace / "result-schema.json"
        output_path = workspace / "result.json"
        schema_path.write_text(json.dumps(RESULT_SCHEMA, separators=(",", ":")))
        command = _codex_command(
            request,
            workspace=workspace,
            schema_path=schema_path,
            output_path=output_path,
        )
        try:
            completed = subprocess.run(
                command,
                input=_prompt(request),
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
        result = _validate_result(
            _decode_result(output_path.read_text()), scope=request.scope
        )

    result["runtime"] = {
        "provider": "codex",
        "model": request.resolved_model,
        "depth": request.depth,
        "elapsed_ms": round((time.monotonic() - started) * 1000),
        "run_id": str(uuid.uuid4()),
        "fresh_session": True,
        "persisted": False,
    }
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docsys research",
        description="Answer one FlowForm question in a fresh local Codex session.",
    )
    parser.add_argument("question", help="exact research question")
    parser.add_argument(
        "--depth",
        choices=sorted(DEPTHS),
        default="quick",
        help="quick or thorough model profile (default: quick)",
    )
    parser.add_argument("--model", help="override the profile model")
    parser.add_argument("--scope", help="repository-relative search scope")
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="output format (default: text)",
    )
    return parser


def _print_text(result: dict[str, Any]) -> None:
    print(result["answer"])
    print()
    print(
        f"confidence: {result['confidence']} | basis: {result['basis']} | "
        f"model: {result['runtime']['model']}"
    )
    for finding in result["findings"]:
        print(f"- {finding['claim']}")
        for source in finding["sources"]:
            print(
                f"  {source['path']}:{source['start_line']}-{source['end_line']} "
                f"({source['kind']})"
            )
    for heading, key in (
        ("contradictions", "contradictions"),
        ("unresolved", "unresolved"),
    ):
        if result[key]:
            print(f"{heading}:")
            for item in result[key]:
                print(f"- {item}")


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        result = run_research(
            ResearchRequest(
                question=args.question,
                depth=args.depth,
                model=args.model,
                scope=args.scope,
            )
        )
    except (ValueError, ResearchRuntimeError) as error:
        parser.error(str(error))

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        _print_text(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
