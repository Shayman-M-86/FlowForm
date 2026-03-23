from __future__ import annotations

import logging
from typing import Any

from flask import g

AUDIT_LOGGER = logging.getLogger("app.audit")


def audit_event(
    *,
    event_type: str,
    user_id: str | None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Record a structured audit event for a user action.

    Args:
        event_type: Type of event (for example, "form.created").
        user_id: Identifier of the acting user, if available.
        resource_type: Kind of resource affected by the action.
        resource_id: Identifier of the affected resource.
        metadata: Optional extra context to include in the audit log.
    """
    AUDIT_LOGGER.info(
        "Audit event recorded",
        extra={
            "request_id": getattr(g, "request_id", None),
            "user_id": user_id,
            "event_type": event_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "metadata": metadata or {},
        },
    )
