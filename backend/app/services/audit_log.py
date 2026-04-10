from sqlalchemy.orm import Session

from app.schema.orm.core.audit_log import AuditLog


class AuditLogService:
    """Create audit log records for important application actions."""

    def log_action(
        self,
        db: Session,
        *,
        user_id: int | None,
        action: str,
        entity_type: str,
        entity_id: int | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        """Add an audit log record to the current transaction."""
        log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            log_metadata=metadata,
        )
        db.add(log)
        db.flush()
        return log
