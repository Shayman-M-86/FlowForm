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
from typing import Any

from .model import ROOT

DEFAULT_QUICK_MODEL = "gpt-5.6-terra"
DEFAULT_THOROUGH_MODEL = "gpt-5.6-sol"
DEPTHS = frozenset({"quick", "thorough"})
_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")
_PROMPT_PATH = Path(__file__).with_name("prompts") / "research.md"

RESULT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "basis": {
            "type": "string",
            "enum": ["documentation", "implementation", "mixed"],
        },
        "findings": {
            "type": "array",
            "minItems": 1,
            "maxItems": 12,
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "sources": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 6,
                        "items": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "start_line": {"type": "integer", "minimum": 1},
                                "end_line": {"type": "integer", "minimum": 1},
                                "kind": {
                                    "type": "string",
                                    "enum": [
                                        "documentation",
                                        "implementation",
                                        "test",
                                        "configuration",
                                    ],
                                },
                            },
                            "required": ["path", "start_line", "end_line", "kind"],
                            "additionalProperties": False,
                        },
                    },
                    "snippet": {"type": ["string", "null"]},
                },
                "required": ["claim", "sources", "snippet"],
                "additionalProperties": False,
            },
        },
        "contradictions": {"type": "array", "items": {"type": "string"}},
        "unresolved": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "answer",
        "confidence",
        "basis",
        "findings",
        "contradictions",
        "unresolved",
    ],
    "additionalProperties": False,
}


class ResearchRuntimeError(RuntimeError):
    """A fresh local Codex research process failed."""


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
    instructions = _PROMPT_PATH.read_text().strip()
    payload = (
        json.dumps(
            {
                "scope": request.scope or "repository-wide",
                "depth": request.depth,
                "question": request.question,
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


def _validate_text_list(value: object, *, name: str, maximum: int = 20) -> list[str]:
    if not isinstance(value, list) or len(value) > maximum:
        raise ResearchRuntimeError(f"{name} must be a bounded array")
    if any(not isinstance(item, str) for item in value):
        raise ResearchRuntimeError(f"{name} must contain strings")
    return [item.strip() for item in value if item.strip()]


def _validate_source(value: object, *, scope: str | None = None) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ResearchRuntimeError("finding source must be an object")
    path_value = value.get("path")
    start_line = value.get("start_line")
    end_line = value.get("end_line")
    kind = value.get("kind")
    if not isinstance(path_value, str):
        raise ResearchRuntimeError("source path must be a string")
    path = PurePosixPath(path_value)
    if path_value.startswith("/") or any(
        part in {"", ".", ".."} for part in path.parts
    ):
        raise ResearchRuntimeError("source path must be repository-relative")
    normalized_path = path.as_posix()
    if scope is not None and not (
        normalized_path == scope or normalized_path.startswith(scope + "/")
    ):
        raise ResearchRuntimeError(
            f"cited source is outside requested scope: {path_value}"
        )
    resolved = ROOT.joinpath(*path.parts)
    if resolved.is_symlink() or not resolved.is_file():
        raise ResearchRuntimeError(f"cited source does not exist: {path_value}")
    if (
        isinstance(start_line, bool)
        or not isinstance(start_line, int)
        or isinstance(end_line, bool)
        or not isinstance(end_line, int)
        or start_line < 1
        or end_line < start_line
    ):
        raise ResearchRuntimeError("source line range is invalid")
    line_count = len(resolved.read_text(errors="replace").splitlines())
    if end_line > max(1, line_count):
        raise ResearchRuntimeError(f"cited line is beyond end of file: {path_value}")
    if kind not in {"documentation", "implementation", "test", "configuration"}:
        raise ResearchRuntimeError("source kind is invalid")
    return {
        "path": path.as_posix(),
        "start_line": start_line,
        "end_line": end_line,
        "kind": kind,
    }


def _validate_result(
    value: dict[str, Any], *, scope: str | None = None
) -> dict[str, Any]:
    answer = value.get("answer")
    confidence = value.get("confidence")
    basis = value.get("basis")
    findings = value.get("findings")
    if not isinstance(answer, str) or not answer.strip():
        raise ResearchRuntimeError("answer must be a non-empty string")
    if confidence not in {"high", "medium", "low"}:
        raise ResearchRuntimeError("confidence is invalid")
    if basis not in {"documentation", "implementation", "mixed"}:
        raise ResearchRuntimeError("basis is invalid")
    if not isinstance(findings, list) or not findings or len(findings) > 12:
        raise ResearchRuntimeError("findings must contain between 1 and 12 items")

    clean_findings = []
    for finding in findings:
        if not isinstance(finding, dict) or not isinstance(finding.get("claim"), str):
            raise ResearchRuntimeError("finding must contain a claim")
        sources = finding.get("sources")
        if not isinstance(sources, list) or not sources or len(sources) > 6:
            raise ResearchRuntimeError("finding must contain between 1 and 6 sources")
        snippet = finding.get("snippet")
        if snippet is not None and not isinstance(snippet, str):
            raise ResearchRuntimeError("finding snippet must be a string or null")
        clean_findings.append(
            {
                "claim": finding["claim"].strip(),
                "sources": [
                    _validate_source(source, scope=scope) for source in sources
                ],
                "snippet": snippet,
            }
        )
    return {
        "answer": answer.strip(),
        "confidence": confidence,
        "basis": basis,
        "findings": clean_findings,
        "contradictions": _validate_text_list(
            value.get("contradictions"), name="contradictions"
        ),
        "unresolved": _validate_text_list(value.get("unresolved"), name="unresolved"),
    }


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
            workspace=ROOT,
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
