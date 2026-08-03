"""Contracts and validation for source-backed Docsys research."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
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

from ..core.model import ROOT

DEFAULT_QUICK_MODEL = "sonnet"
DEFAULT_THOROUGH_MODEL = "opus"
DEFAULT_CODEX_QUICK_MODEL = "gpt-5.6-terra"
DEFAULT_CODEX_THOROUGH_MODEL = "gpt-5.6-sol"
DEPTHS = frozenset({"quick", "thorough"})
PROVIDERS = frozenset({"auto", "claude", "codex"})
_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")


class ResearchRuntimeError(RuntimeError):
    """A local research provider failed."""


class ResearchSource(BaseModel):
    """One source citation returned by an isolated research session."""

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
    def _validate_lines(self) -> ResearchSource:
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
    """Validated result shape shared by the research providers."""

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
    provider: str = "auto"

    def __post_init__(self) -> None:
        question = self.question.strip()
        depth = self.depth.casefold().strip()
        provider = self.provider.casefold().strip()
        if not question:
            raise ValueError("question must not be empty")
        if len(question) > 4_000:
            raise ValueError("question must contain at most 4000 characters")
        if depth not in DEPTHS:
            raise ValueError("depth must be one of: quick, thorough")
        if provider not in PROVIDERS:
            raise ValueError("provider must be one of: auto, claude, codex")
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
        object.__setattr__(self, "provider", provider)
        if self.model is not None:
            object.__setattr__(self, "model", self.model.strip())

    @property
    def resolved_model(self) -> str:
        return (
            self.resolved_codex_model
            if self.provider == "codex"
            else self.resolved_claude_model
        )

    @property
    def resolved_claude_model(self) -> str:
        return self.model or (
            DEFAULT_QUICK_MODEL if self.depth == "quick" else DEFAULT_THOROUGH_MODEL
        )

    @property
    def resolved_codex_model(self) -> str:
        override = self.model if self.provider == "codex" else None
        return override or (
            DEFAULT_CODEX_QUICK_MODEL
            if self.depth == "quick"
            else DEFAULT_CODEX_THOROUGH_MODEL
        )

    @property
    def reasoning_effort(self) -> Literal["low", "high"]:
        return "low" if self.depth == "quick" else "high"

    @property
    def codex_reasoning_effort(self) -> Literal["medium", "high"]:
        return "medium" if self.depth == "quick" else "high"

    @property
    def max_turns(self) -> int:
        return 8 if self.depth == "quick" else 16

    @property
    def timeout_seconds(self) -> int:
        return 120 if self.depth == "quick" else 240


def validate_result(
    value: dict[str, Any], *, scope: str | None = None
) -> dict[str, Any]:
    """Validate the result contract and every repository citation."""
    try:
        result = ResearchResult.model_validate(value, context={"scope": scope})
    except ValidationError as exc:
        messages = [str(error["msg"]) for error in exc.errors()]
        raise ResearchRuntimeError("; ".join(messages)) from exc
    return result.model_dump(mode="json")
