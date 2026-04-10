from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schema.orm.core.permission import Permission


def list_permission_names(db: Session) -> set[str]:
    """Return all permission names in the database."""
    return set(db.scalars(select(Permission.name)))


def create_permissions(db: Session, names: list[str]) -> list[Permission]:
    """Create permission rows for the given names."""
    permissions = [Permission(name=name) for name in names]
    db.add_all(permissions)
    db.flush()
    return permissions