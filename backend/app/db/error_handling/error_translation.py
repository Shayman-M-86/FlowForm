from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from psycopg.errors import CheckViolation, ForeignKeyViolation, UniqueViolation
from sqlalchemy.exc import DBAPIError

from app.domain.errors import AppError

ErrorFactory = Callable[[Any, DBAPIError], AppError]
ContextExtractor = Callable[[Any], Any]


@dataclass(frozen=True)
class DbErrorRule:
    """Map one database error key to one application error."""

    key: str
    error_factory: ErrorFactory
    extractor: ContextExtractor | None = None
    driver_error: type[BaseException] | None = None

    def matches(self, exc: DBAPIError) -> bool:
        if self.driver_error is not None and not isinstance(exc.orig, self.driver_error):
            return False

        return self.key == get_db_error_key(exc)

    def build_error(self, context: Any, exc: DBAPIError) -> AppError:
        payload = self.extractor(context) if self.extractor is not None else context
        return self.error_factory(payload, exc)


def error_factory(error: AppError) -> ErrorFactory:
    """Wrap a fixed AppError as a factory."""
    return lambda _context, _exc: error


def get_constraint_name(exc: DBAPIError) -> str | None:
    """Return the failing constraint name, if present."""
    diag = getattr(exc.orig, "diag", None)
    return getattr(diag, "constraint_name", None)


def get_message_primary(exc: DBAPIError) -> str | None:
    """Return the primary DB error message, if present."""
    diag = getattr(exc.orig, "diag", None)
    return getattr(diag, "message_primary", None)


def get_db_error_key(exc: DBAPIError) -> str | None:
    """Return the best available key for matching a DB error."""
    constraint_name = get_constraint_name(exc)
    if constraint_name:
        return constraint_name

    message_primary = get_message_primary(exc)
    if message_primary:
        return message_primary

    if exc.orig is not None:
        return str(exc.orig)

    return None


def unique_rule(key: str, error_factory: ErrorFactory, *, extractor: ContextExtractor | None = None) -> DbErrorRule:
    return DbErrorRule(
        key=key,
        error_factory=error_factory,
        extractor=extractor,
        driver_error=UniqueViolation,
    )


def foreign_key_rule(
    key: str,
    error_factory: ErrorFactory,
    *,
    extractor: ContextExtractor | None = None,
) -> DbErrorRule:
    return DbErrorRule(
        key=key,
        error_factory=error_factory,
        extractor=extractor,
        driver_error=ForeignKeyViolation,
    )


def check_rule(key: str, error_factory: ErrorFactory, *, extractor: ContextExtractor | None = None) -> DbErrorRule:
    return DbErrorRule(
        key=key,
        error_factory=error_factory,
        extractor=extractor,
        driver_error=CheckViolation,
    )


def message_rule(
    message: str,
    error_factory: ErrorFactory,
    *,
    extractor: ContextExtractor | None = None,
) -> DbErrorRule:
    """Match trigger-raised or other DB errors by message text."""
    return DbErrorRule(
        key=message,
        error_factory=error_factory,
        extractor=extractor,
        driver_error=None,
    )


def translate_db_error(
    exc: DBAPIError,
    *,
    context: Any,
    rules: tuple[DbErrorRule, ...],
) -> tuple[AppError | None, DbErrorRule | None]:
    for rule in rules:
        if rule.matches(exc):
            return rule.build_error(context, exc), rule
    return None, None
