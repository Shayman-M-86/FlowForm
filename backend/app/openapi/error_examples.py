"""Derive OpenAPI error examples from real ``AppError`` subclasses and schemas.

This module is the bridge between the runtime error layer and the
documentation layer: the spec builder calls into here to produce per-status
example payloads, and the examples are always in sync with the code that
actually raises them.

Two derivation paths:

1. **AppError subclasses** — ``AppError.__subclasses__()`` is walked
   recursively. Each concrete class is instantiated with synthesised stub
   arguments (zero-arg first; otherwise primitives matching the constructor
   signature) so its ``code`` / ``message`` / ``status_code`` can be read
   off the instance. Examples are grouped by status code.

2. **DbIntegrityError instances** — these are not per-class errors but
   per-rule constructions. We walk ``RULES_BY_CONTEXT`` and call each rule
   factory with a stub context to build a representative example for every
   registered DB constraint translation.

3. **Pydantic 422** — built by deliberately failing a known request schema
   with a malformed payload and routing the resulting ``ValidationError``
   through ``normalize_pydantic_errors``. This guarantees the example
   matches the real handler output.
"""

from __future__ import annotations

import inspect
import logging
from typing import Any, get_args, get_origin

from pydantic import ValidationError

from app.api.utils.validation import normalize_pydantic_errors
from app.core.errors import AppError, AuthError
from app.db.error_handling.errors import DbIntegrityError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# AppError discovery + stub instantiation
# ---------------------------------------------------------------------------


# Bases that should never appear as their own example because they are
# abstract / parameterised — their concrete usages either subclass them
# (AuthError → InvalidIdTokenSubjectError etc.) or construct them per rule
# (DbIntegrityError, populated by _iter_db_integrity_examples). The
# subclasses / rule-derived instances still produce examples normally.
_SKIP_BASES: tuple[type[AppError], ...] = (
    AuthError,
    DbIntegrityError,
)


def _ensure_error_modules_imported() -> None:
    """Force-import every module that defines ``AppError`` subclasses.

    ``__subclasses__()`` only sees classes whose modules have been imported,
    so any caller of ``build_examples_by_status`` that has not touched the
    relevant modules would otherwise see a partial registry. These imports
    are idempotent.
    """
    import app.db.error_handling.integrity_rules  # registers rules in RULES_BY_CONTEXT
    import app.domain.errors
    import app.middleware.rate_limit.errors

    _ = (app.domain.errors, app.middleware.rate_limit.errors, app.db.error_handling.integrity_rules)


def _iter_app_error_subclasses(root: type[AppError] = AppError) -> list[type[AppError]]:
    """Walk ``AppError.__subclasses__()`` recursively, returning concrete leaves."""
    _ensure_error_modules_imported()

    seen: set[type[AppError]] = set()
    out: list[type[AppError]] = []

    def visit(cls: type[AppError]) -> None:
        for sub in cls.__subclasses__():
            if sub in seen:
                continue
            seen.add(sub)
            visit(sub)
            out.append(sub)

    visit(root)
    return out


def _stub_value_for(annotation: Any) -> Any:
    """Best-effort stub value for a constructor parameter annotation.

    Returns ``None`` for optional types, sensible primitives for ``int`` /
    ``str`` / ``bool``, empty containers for ``list`` / ``dict``, and ``None``
    as a final fallback (the caller will catch ``TypeError`` if a particular
    class refuses ``None``).
    """
    if annotation is inspect.Parameter.empty:
        return ""

    origin = get_origin(annotation)
    if origin is None:
        if annotation is int:
            return 0
        if annotation is float:
            return 0.0
        if annotation is bool:
            return False
        if annotation is str:
            return "<example>"
        if annotation is bytes:
            return b""
        return None

    # Optional[X] / X | None — pick the non-None arm.
    if origin is type(None):
        return None
    args = [a for a in get_args(annotation) if a is not type(None)]
    if not args:
        return None
    if origin in (list, tuple, set, frozenset):
        return origin()
    if origin is dict:
        return {}
    return _stub_value_for(args[0])


def _instantiate_for_doc(cls: type[AppError]) -> AppError | None:
    """Try to construct ``cls`` for documentation purposes.

    Strategy: call with no args first (covers errors that take no params);
    otherwise build stub kwargs from the signature.

    Returns ``None`` if the class cannot be constructed at all — that gets
    logged so a maintainer can decide whether to add an explicit override.
    """
    try:
        return cls()  # type: ignore[call-arg]
    except TypeError:
        pass

    try:
        sig = inspect.signature(cls)
    except (TypeError, ValueError):
        logger.warning("Could not introspect signature for %s", cls.__name__)
        return None

    kwargs: dict[str, Any] = {}
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        if param.default is not inspect.Parameter.empty:
            continue
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        kwargs[name] = _stub_value_for(param.annotation)

    try:
        return cls(**kwargs)
    except TypeError as exc:
        logger.warning("Could not construct example for %s: %s", cls.__name__, exc)
        return None


def _to_payload(exc: AppError) -> dict[str, Any]:
    """Build the JSON payload the handler would emit for this error.

    Mirrors ``api/utils/errors.py:_error_response`` — ``details`` is omitted
    when empty.
    """
    payload: dict[str, Any] = {"code": exc.code, "message": exc.message}
    if exc.details:
        payload["details"] = exc.details
    return payload


def _example_key(cls: type[AppError]) -> str:
    """OpenAPI examples-map key derived from the class name."""
    name = cls.__name__
    if name.endswith("Error"):
        name = name[: -len("Error")]
    return _snake_case(name)


def _snake_case(name: str) -> str:
    out: list[str] = []
    for i, ch in enumerate(name):
        if ch.isalnum():
            if ch.isupper() and i > 0 and out and out[-1] != "_" and not name[i - 1].isupper():
                out.append("_")
            out.append(ch.lower())
        else:
            if out and out[-1] != "_":
                out.append("_")
    return "".join(out).strip("_")


# ---------------------------------------------------------------------------
# DbIntegrityError — derived from the rule registry
# ---------------------------------------------------------------------------


def _iter_db_integrity_examples() -> list[tuple[AppError, str]]:
    """Walk RULES_BY_CONTEXT and synthesise one example per rule.

    Rules construct a ``DbIntegrityError`` from a context dict. We feed them
    a permissive ``StubContext`` whose ``__getitem__`` returns a placeholder
    for any key so the rule's f-string interpolation succeeds.

    Returns ``(error_instance, example_key)`` tuples.
    """
    try:
        from app.db.error_handling.integrity_rules import RULES_BY_CONTEXT
    except ImportError:
        logger.warning("Could not import RULES_BY_CONTEXT; skipping DB integrity examples")
        return []

    class StubContext(dict[str, Any]):
        def __missing__(self, key: str) -> str:
            return f"<{key}>"

    stub_ctx = StubContext()
    out: list[tuple[AppError, str]] = []

    for rules in RULES_BY_CONTEXT.values():
        for rule in rules:
            try:
                error = rule.error_factory(stub_ctx, None)  # type: ignore[arg-type]
            except Exception as exc:  # pragma: no cover - documentation best-effort
                logger.warning("Could not build example for db rule %s: %s", rule.key, exc)
                continue
            out.append((error, _snake_case(rule.key)))

    return out


# ---------------------------------------------------------------------------
# Pydantic 422 — derived from a real schema failure
# ---------------------------------------------------------------------------


def _build_pydantic_example() -> dict[str, Any]:
    """Produce a realistic 422 payload by failing a real request schema.

    Uses ``CreateNodeRequest`` because it exercises nested + discriminated
    union validation, which produces a rich, representative error array.
    Falls back to a hand-rolled minimal example if the import or the
    validation fails to raise.
    """
    try:
        from app.schema.api.requests.content.node import CreateNodeRequest
    except ImportError:
        logger.warning("Could not import CreateNodeRequest for 422 example")
        return _fallback_pydantic_example()

    try:
        CreateNodeRequest.model_validate(
            {"type": "question", "sort_key": "not-an-int", "content": {}}
        )
    except ValidationError as exc:
        return {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed.",
            "details": {"errors": normalize_pydantic_errors(exc)},
        }
    except Exception as exc:  # pragma: no cover
        logger.warning("Unexpected error producing pydantic example: %s", exc)

    return _fallback_pydantic_example()


def _fallback_pydantic_example() -> dict[str, Any]:
    return {
        "code": "VALIDATION_ERROR",
        "message": "Request validation failed.",
        "details": {
            "errors": [
                {
                    "field": "sort_key",
                    "message": "Input should be a valid integer.",
                    "type": "int_parsing",
                }
            ]
        },
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_examples_by_status() -> dict[int, dict[str, dict[str, Any]]]:
    """Return ``{status_code: {example_name: openapi_example}}``.

    Each inner value follows the OpenAPI 3 example object shape
    (``{"summary": str, "value": dict}``) so it slots directly into a
    response's ``examples:`` map.
    """
    grouped: dict[int, dict[str, dict[str, Any]]] = {}

    # 1. Real AppError subclasses.
    for cls in _iter_app_error_subclasses():
        if cls in _SKIP_BASES:
            continue
        instance = _instantiate_for_doc(cls)
        if instance is None:
            continue
        status = instance.status_code
        key = _example_key(cls)
        grouped.setdefault(status, {})[key] = {
            "summary": cls.__name__,
            "value": _to_payload(instance),
        }

    # 2. DbIntegrityError variations from the rule registry.
    for error, key in _iter_db_integrity_examples():
        status = error.status_code
        grouped.setdefault(status, {})[key] = {
            "summary": f"DB rule: {error.code}",
            "value": _to_payload(error),
        }

    # 3. Pydantic 422.
    pydantic_example = _build_pydantic_example()
    grouped.setdefault(422, {})["pydantic_field_validation"] = {
        "summary": "Pydantic field validation failure",
        "value": pydantic_example,
    }

    # 4. Static fallbacks for statuses that no AppError currently covers but
    # the handler layer can still emit (HTTPException, generic 500).
    grouped.setdefault(500, {})["internal_server_error"] = {
        "summary": "Generic server error",
        "value": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred.",
        },
    }

    return grouped
