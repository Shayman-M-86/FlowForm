from __future__ import annotations

import logging
from collections.abc import Iterable

from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.error_handling.error_translation import DbErrorRule, get_db_error_key, translate_db_error
from app.db.error_handling.integrity_rules import RULES_BY_CONTEXT, RuleContext, allowed_parameters

logger = logging.getLogger(__name__)


def get_rules_for_context(context: RuleContext) -> tuple[DbErrorRule, ...]:
    """Return the first matching rule set for the context type or its parents."""
    for cls in type(context).__mro__:
        rules = RULES_BY_CONTEXT.get(cls)
        if rules is not None:
            return rules
    return ()


def summarize_context(context: RuleContext) -> dict[str, object]:
    summary: dict[str, object] = {"context_type": type(context).__name__}

    for key in allowed_parameters:
        if hasattr(context, key):
            summary[key] = getattr(context, key)

    return summary


def summarize_contexts(contexts: Iterable[RuleContext]) -> dict[str, object]:
    """Return compact summaries for multiple contexts."""
    items = list(contexts)

    return {
        "context_types": [type(ctx).__name__ for ctx in items],
        "contexts": [summarize_context(ctx) for ctx in items],
    }


def _translate_db_error_for_contexts(
    exc: DBAPIError,
    *,
    contexts: Iterable[RuleContext],
) -> tuple[AppError | None, DbErrorRule | None, RuleContext | None]:
    for context in contexts:
        rules = get_rules_for_context(context)
        mapped, matched_rule = translate_db_error(exc, context=context, rules=rules)
        if mapped is not None:
            return mapped, matched_rule, context

    return None, None, None


def commit_with_err_handle(db: Session, *, contexts: Iterable[RuleContext] | None = None) -> None:
    """Commit and auto-translate DB errors using multiple candidate contexts."""
    context_list = list(contexts or [])

    try:
        db.commit()
    except DBAPIError as exc:
        db.rollback()

        mapped, matched_rule, matched_context = _translate_db_error_for_contexts(
            exc,
            contexts=context_list,
        )
        error_key = get_db_error_key(exc)

        if mapped is not None:
            logger.debug(
                "Translated database error during commit",
                extra={
                    "db_error_key": error_key,
                    "matched_rule_key": matched_rule.key if matched_rule else None,
                    "app_error_code": mapped.code,
                    "app_error_status": mapped.status_code,
                    "matched_context": summarize_context(matched_context) if matched_context is not None else None,
                    **summarize_contexts(context_list),
                },
            )
            raise mapped from None

        logger.exception(
            "Unhandled database error during commit",
            extra={
                "db_error_key": error_key,
                **summarize_contexts(context_list),
            },
            exc_info=exc,
        )
        raise
    except Exception:
        db.rollback()
        logger.exception(
            "Unhandled non-database error during commit",
            extra=summarize_contexts(context_list),
        )
        raise


def flush_with_err_handle(db: Session, *, contexts: Iterable[RuleContext] | None = None) -> None:
    """Flush and auto-translate DB errors using multiple candidate contexts."""
    context_list = list(contexts or [])

    try:
        db.flush()
    except DBAPIError as exc:
        db.rollback()

        mapped, matched_rule, matched_context = _translate_db_error_for_contexts(
            exc,
            contexts=context_list,
        )
        error_key = get_db_error_key(exc)

        if mapped is not None:
            logger.debug(
                "Translated database error during flush",
                extra={
                    "db_error_key": error_key,
                    "matched_rule_key": matched_rule.key if matched_rule else None,
                    "app_error_code": mapped.code,
                    "app_error_status": mapped.status_code,
                    "matched_context": summarize_context(matched_context) if matched_context is not None else None,
                    **summarize_contexts(context_list),
                },
            )
            raise mapped from None

        logger.exception(
            "Unhandled database error during flush",
            extra={
                "db_error_key": error_key,
                **summarize_contexts(context_list),
            },
            exc_info=exc,
        )
        raise
