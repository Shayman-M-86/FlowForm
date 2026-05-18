"""Exception types raised by the DB integrity-translation layer.

Two distinct shapes:

- ``DbIntegrityError`` — a Postgres constraint violation that was matched by
  a rule in ``integrity_rules.py`` and translated into a known, stable
  ``code``. Status defaults to 409 (most rules) but can be overridden to 500
  for CHECK violations on server-controlled fields where the client could
  not have caused the error.

- ``UnhandledDbIntegrityError`` — a Postgres constraint violation that
  matched no rule. Reaching this almost always means a new rule is needed
  or that an upstream layer (Pydantic / domain rule) was bypassed. Always
  500; the ``details`` payload includes the failing constraint name and a
  summary of the contexts passed to the commit/flush helper so operators
  can find the bypassed path.
"""

from __future__ import annotations

from typing import Any

from app.core.errors import AppError


class DbIntegrityError(AppError):
    """Translated Postgres constraint violation with a known ``code``.

    Positional signature mirrors ``AppError`` for convenience in rule
    factories: ``DbIntegrityError(status_code, code, message)``. The
    ``constraint_name`` attribute is attached by the registry after
    construction (rules do not need to repeat the constraint key).
    """

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
        *,
        constraint_name: str | None = None,
    ) -> None:
        super().__init__(
            status_code=status_code,
            code=code,
            message=message,
            details=details or {},
        )
        self.constraint_name = constraint_name


class UnhandledDbIntegrityError(AppError):
    """Postgres constraint violation that no rule covered.

    Always 500: reaching this means either a missing rule or an upstream
    bypass — both are server-side bugs from the client's perspective.
    """

    def __init__(
        self,
        *,
        constraint_name: str | None,
        error_key: str | None,
        context_summary: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            status_code=500,
            code="UNHANDLED_DB_INTEGRITY_ERROR",
            message="An unexpected database integrity error occurred.",
            details={
                "constraint_name": constraint_name,
                "error_key": error_key,
                "context": context_summary or {},
            },
        )
