"""Source-backed research powered by local Claude Code with Codex fallback."""

from .models import (
    DEFAULT_CODEX_QUICK_MODEL,
    DEFAULT_CODEX_THOROUGH_MODEL,
    DEFAULT_QUICK_MODEL,
    DEFAULT_THOROUGH_MODEL,
    DEPTHS,
    PROVIDERS,
    RESULT_SCHEMA,
    ResearchRequest,
    ResearchRuntimeError,
    validate_result,
)
from .providers import run_research

__all__ = [
    "DEFAULT_CODEX_QUICK_MODEL",
    "DEFAULT_CODEX_THOROUGH_MODEL",
    "DEFAULT_QUICK_MODEL",
    "DEFAULT_THOROUGH_MODEL",
    "DEPTHS",
    "PROVIDERS",
    "RESULT_SCHEMA",
    "ResearchRequest",
    "ResearchRuntimeError",
    "run_research",
    "validate_result",
]
