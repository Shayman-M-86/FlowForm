from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.error_handling import flush_with_err_handle
from app.schema.orm.core.permission import Permission


def list_permission_names(db: Session) -> set[str]:
    """Return all permission names in the database."""
    return set(db.scalars(select(Permission.name)))


def get_permissions_by_names(db: Session, names: list[str]) -> list[Permission]:
    """Fetch Permission rows for the given names."""
    return list(db.scalars(select(Permission).where(Permission.name.in_(names))))


def create_permissions(db: Session, names: list[str]) -> list[Permission]:
    """Create permission rows for the given names."""
    permissions = [Permission(name=name) for name in names]
    db.add_all(permissions)
    flush_with_err_handle(db)
    return permissions
